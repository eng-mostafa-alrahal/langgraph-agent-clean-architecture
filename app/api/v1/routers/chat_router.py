from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    get_current_user_id,
    get_execute_graph_uc,
    get_stream_graph_events_uc,
)
from app.api.v1.schemas.chat_schema import ChatRequest, ChatResponse
from app.modules.agent_orchestration.application.use_cases.execute_graph_uc import (
    ExecuteGraphUseCase,
)
from app.modules.agent_orchestration.application.use_cases.stream_graph_events_uc import (
    StreamGraphEventsUseCase,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


def _message_content_to_str(content: object) -> str:
    """Normalize LangChain message content (str or provider-specific blocks) for JSON responses."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def _message_to_stream_dict(msg: object) -> dict[str, Any]:
    """Compact, JSON-friendly view of a LangChain message (no raw repr)."""
    content = _message_content_to_str(getattr(msg, "content", msg))
    out: dict[str, Any] = {
        "type": getattr(msg, "type", None)
        or getattr(msg.__class__, "__name__", "message").replace("Message", "").lower(),
        "content": content,
    }
    mid = getattr(msg, "id", None)
    if mid:
        out["id"] = mid
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        out["tool_calls"] = tool_calls
    rm = getattr(msg, "response_metadata", None) or {}
    if isinstance(rm, dict):
        if rm.get("model_name"):
            out["model"] = rm["model_name"]
        usage = rm.get("token_usage") or rm.get("usage")
        if isinstance(usage, dict) and usage:
            out["usage"] = {
                k: usage[k]
                for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                if k in usage
            }
    return out


def _jsonify_stream_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonify_stream_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify_stream_value(x) for x in value]
    if hasattr(value, "content") and (
        hasattr(value, "type") or value.__class__.__name__.endswith("Message")
    ):
        return _message_to_stream_dict(value)
    return str(value)


def _stream_event_to_jsonable(event: dict[str, Any]) -> dict[str, Any]:
    """Convert LangGraph astream chunk (per-node state updates) to JSON-safe data."""
    out: dict[str, Any] = {}
    for node_name, payload in event.items():
        if isinstance(payload, dict):
            chunk: dict[str, Any] = {}
            for k, v in payload.items():
                if k == "messages" and isinstance(v, list):
                    chunk[k] = [_message_to_stream_dict(m) for m in v]
                else:
                    chunk[k] = _jsonify_stream_value(v)
            out[node_name] = chunk
        else:
            out[node_name] = _jsonify_stream_value(payload)
    return out


def _stream_chunk_has_content(payload: dict[str, Any]) -> bool:
    """Skip LangGraph chunks where every node returned an empty update (e.g. no-op error_handler)."""
    return any(bool(v) for v in payload.values())


def _compact_stream_payload(full: dict[str, Any]) -> dict[str, Any] | None:
    """One SSE object per graph step: graph node name + latest assistant turn only (no full history)."""
    for node_name, payload in full.items():
        if not isinstance(payload, dict):
            continue
        messages = payload.get("messages")
        if not isinstance(messages, list):
            continue
        last_ai: dict[str, Any] | None = None
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("type") == "ai":
                last_ai = m
                break
        if not last_ai:
            return {"node": node_name, "assistant": None}
        assistant: dict[str, Any] = {"content": last_ai.get("content", "")}
        if last_ai.get("id"):
            assistant["id"] = last_ai["id"]
        if last_ai.get("model"):
            assistant["model"] = last_ai["model"]
        if last_ai.get("usage"):
            assistant["usage"] = last_ai["usage"]
        if last_ai.get("tool_calls"):
            assistant["tool_calls"] = last_ai["tool_calls"]
        return {"node": node_name, "assistant": assistant}
    return None


def _compact_chunk_is_meaningful(payload: dict[str, Any]) -> bool:
    a = payload.get("assistant")
    if not isinstance(a, dict):
        return False
    return bool(a.get("content") or a.get("tool_calls"))


@router.post(
    "/",
    response_model=ChatResponse,
    summary="Send message (single response)",
    description=(
        "Run the agent with a user message and return one final reply.\n\n"
        "When the response has `interrupted: true` the agent is waiting for "
        "human approval.  Use `POST /runs/{thread_id}/resume` to continue."
    ),
)
async def chat(
    body: Annotated[
        ChatRequest,
        Body(description="Chat payload containing the user message and target session ID."),
    ],
    user_id=Depends(get_current_user_id),
    uc: ExecuteGraphUseCase = Depends(get_execute_graph_uc),
) -> ChatResponse:
    result = await uc.execute(
        body.message,
        session_id=str(body.session_id),
        user_id=str(user_id),
    )

    interrupted = bool(result.get("__interrupted"))
    approval_request = result.get("__interrupt_payload") if interrupted else None

    messages = result.get("messages", [])
    reply = _message_content_to_str(messages[-1].content) if messages else ""

    return ChatResponse(
        session_id=body.session_id,
        reply=reply,
        interrupted=interrupted,
        thread_id=str(body.session_id) if interrupted else None,
        approval_request=approval_request,
    )


@router.post(
    "/stream",
    summary="Send message (streaming response)",
    description=(
        "Run the agent and stream Server-Sent Events (SSE). "
        "Default (`stream_detail=content`) sends a small JSON per line: `node` and `assistant` "
        "(latest AI message only, plus optional usage/tool_calls). "
        "Use `stream_detail=full` for raw per-node state including full message history. "
        "Ends with `data: [DONE]`."
    ),
)
async def chat_stream(
    body: Annotated[
        ChatRequest,
        Body(description="Streaming chat payload with message and session ID."),
    ],
    user_id=Depends(get_current_user_id),
    uc: StreamGraphEventsUseCase = Depends(get_stream_graph_events_uc),
) -> StreamingResponse:
    async def event_generator():
        detail = body.stream_detail
        async for event in uc.execute(
            body.message,
            session_id=str(body.session_id),
            user_id=str(user_id),
        ):
            if isinstance(event, dict):
                full = _stream_event_to_jsonable(event)
                if detail == "full":
                    if not _stream_chunk_has_content(full):
                        continue
                    payload: dict[str, Any] | None = full
                else:
                    payload = _compact_stream_payload(full)
                    if payload is None or not _compact_chunk_is_meaningful(payload):
                        continue
            else:
                payload = {"value": _jsonify_stream_value(event)}
            yield f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
