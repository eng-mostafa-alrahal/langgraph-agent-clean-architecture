"""Chat / agent HTTP endpoints.

This router is a thin delivery adapter: it takes DTOs from the use-case and
serialises them for HTTP. It must not import LangGraph / LangChain types.
"""

from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    get_current_user_id,
    get_execute_graph_uc,
    get_stream_graph_events_uc,
)
from app.api.v1.schemas.chat_schema import ChatRequest, ChatResponse
from app.core.observability.request_context import get_request_id
from app.modules.agent_orchestration.application.dtos.agent_result import (
    AgentEvent,
    AgentMessage,
    is_internal_memory_summary_message,
)
from app.modules.agent_orchestration.application.use_cases.execute_graph_uc import (
    ExecuteGraphUseCase,
)
from app.modules.agent_orchestration.application.use_cases.stream_graph_events_uc import (
    StreamGraphEventsUseCase,
)

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


def _approval_payload(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if hasattr(raw, "model_dump"):
        return raw.model_dump()
    if isinstance(raw, dict):
        return raw
    return {"value": raw}


def _event_has_message_content(messages: list[AgentMessage]) -> bool:
    return any(bool(m.content) or bool(m.tool_calls) for m in messages)


def _compact_event_payload(event: AgentEvent) -> dict[str, Any] | None:
    last_ai: AgentMessage | None = next(
        (
            m
            for m in reversed(event.messages)
            if m.type == "ai" and not is_internal_memory_summary_message(m)
        ),
        None,
    )
    if last_ai is None:
        return None
    content = last_ai.content
    if not content:
        return None
    return {"content": content}


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
    started = perf_counter()
    result = await uc.execute(
        body.message,
        session_id=str(body.session_id),
        user_id=str(user_id),
    )
    elapsed_ms = (perf_counter() - started) * 1000
    logger.info(
        "api.chat completed request_id=%s session_id=%s interrupted=%s elapsed_ms=%.1f",
        get_request_id(),
        body.session_id,
        result.interrupted,
        elapsed_ms,
    )
    return ChatResponse(
        session_id=body.session_id,
        reply=result.last_ai_reply,
        interrupted=result.interrupted,
        thread_id=result.thread_id,
        approval_request=_approval_payload(result.approval_request),
    )


@router.post(
    "/stream",
    summary="Send message (streaming response)",
    description=(
        "Run the agent and stream Server-Sent Events (SSE). "
        "Default (`stream_detail=content`) sends a small JSON per line with only `content` "
        "(latest AI message text only). "
        "Use `stream_detail=full` for the full per-node DTO including message history. "
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
        started = perf_counter()
        chunk_count = 0
        detail = body.stream_detail
        async for event in uc.execute(
            body.message,
            session_id=str(body.session_id),
            user_id=str(user_id),
        ):
            if detail == "full":
                if not (_event_has_message_content(event.messages) or event.updates):
                    continue
                payload: dict[str, Any] | None = event.model_dump()
            else:
                payload = _compact_event_payload(event)
                if payload is None:
                    continue
            chunk_count += 1
            yield f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
        elapsed_ms = (perf_counter() - started) * 1000
        logger.info(
            (
                "api.chat_stream completed request_id=%s session_id=%s "
                "detail=%s chunks=%d elapsed_ms=%.1f"
            ),
            get_request_id(),
            body.session_id,
            detail,
            chunk_count,
            elapsed_ms,
        )
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
