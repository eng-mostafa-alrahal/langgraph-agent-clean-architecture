"""Anti-Corruption Layer: translate LangGraph/LangChain objects into pure DTOs.

The application layer depends only on the DTOs in
``agent_orchestration.application.dtos``.  Everything in this module is an
implementation detail of the LangGraph adapter and must never be imported by
use-cases, routers, or other modules.
"""

from __future__ import annotations

from typing import Any

from app.modules.agent_orchestration.application.dtos.agent_result import (
    AgentEvent,
    AgentMessage,
    AgentRunResult,
    AgentStateSnapshot,
    AgentTaskSnapshot,
    ApprovalRequest,
    MessageRole,
)


_TYPE_TO_ROLE: dict[str, MessageRole] = {
    "human": "human",
    "ai": "ai",
    "system": "system",
    "tool": "tool",
}


def _content_to_str(content: Any) -> str:
    """Normalise LangChain message content (str or provider blocks)."""
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


def _infer_role(raw: Any) -> MessageRole:
    type_attr = getattr(raw, "type", None)
    if isinstance(type_attr, str) and type_attr in _TYPE_TO_ROLE:
        return _TYPE_TO_ROLE[type_attr]

    cls_name = type(raw).__name__.lower()
    for key in _TYPE_TO_ROLE:
        if key in cls_name:
            return _TYPE_TO_ROLE[key]
    return "ai"


def to_agent_message(raw: Any) -> AgentMessage:
    """Map a LangChain ``BaseMessage`` (or look-alike) to :class:`AgentMessage`."""

    content = _content_to_str(getattr(raw, "content", raw))
    role = _infer_role(raw)

    tool_calls = getattr(raw, "tool_calls", None) or None
    mid_raw = getattr(raw, "id", None)
    mid = str(mid_raw) if mid_raw is not None else None

    model: str | None = None
    usage: dict[str, int] | None = None
    rm = getattr(raw, "response_metadata", None)
    if isinstance(rm, dict):
        model_name = rm.get("model_name")
        if isinstance(model_name, str):
            model = model_name
        raw_usage = rm.get("token_usage") or rm.get("usage")
        if isinstance(raw_usage, dict):
            picked = {
                k: int(raw_usage[k])
                for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                if isinstance(raw_usage.get(k), int)
            }
            if picked:
                usage = picked

    return AgentMessage(
        type=role,
        content=content,
        id=mid,
        tool_calls=list(tool_calls) if tool_calls else None,
        model=model,
        usage=usage,
    )


def _messages_from_state(state: Any) -> list[AgentMessage]:
    raw_messages = state.get("messages") if isinstance(state, dict) else None
    if not isinstance(raw_messages, list):
        return []
    return [to_agent_message(m) for m in raw_messages]


def _jsonify(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(x) for x in value]
    if hasattr(value, "content") and (
        hasattr(value, "type") or type(value).__name__.endswith("Message")
    ):
        return to_agent_message(value).model_dump()
    return str(value)


def _as_approval_request(payload: Any) -> ApprovalRequest | dict[str, Any] | None:
    if payload is None:
        return None
    if isinstance(payload, dict):
        return ApprovalRequest.model_validate(payload)
    return {"value": _jsonify(payload)}


def snapshot_is_paused(snapshot: Any) -> bool:
    """True when the checkpoint is waiting for human resume."""
    if getattr(snapshot, "next", None):
        return True
    intr = getattr(snapshot, "interrupts", None) or ()
    if intr:
        return True
    for task in getattr(snapshot, "tasks", None) or ():
        if getattr(task, "interrupts", None):
            return True
    return False


def _interrupt_payload(snapshot: Any) -> Any:
    intr = getattr(snapshot, "interrupts", None) or ()
    if intr:
        return intr[0].value
    for task in getattr(snapshot, "tasks", None) or ():
        t_intr = getattr(task, "interrupts", None) or ()
        if t_intr:
            return t_intr[0].value
    return None


def to_run_result(
    state: Any,
    snapshot: Any,
    *,
    thread_id: str,
) -> AgentRunResult:
    interrupted = snapshot_is_paused(snapshot)
    return AgentRunResult(
        messages=_messages_from_state(state),
        interrupted=interrupted,
        thread_id=thread_id if interrupted else None,
        approval_request=_as_approval_request(_interrupt_payload(snapshot))
        if interrupted
        else None,
    )


def to_agent_events(stream_chunk: Any) -> list[AgentEvent]:
    """Map one ``astream`` chunk to one event per node in that chunk."""

    if not isinstance(stream_chunk, dict):
        return [AgentEvent(node="unknown", updates={"value": _jsonify(stream_chunk)})]

    events: list[AgentEvent] = []
    for node_name, payload in stream_chunk.items():
        if isinstance(payload, dict):
            messages: list[AgentMessage] = []
            updates: dict[str, Any] = {}
            for key, value in payload.items():
                if key == "messages" and isinstance(value, list):
                    messages = [to_agent_message(m) for m in value]
                else:
                    updates[key] = _jsonify(value)
            events.append(
                AgentEvent(node=str(node_name), messages=messages, updates=updates)
            )
        else:
            events.append(
                AgentEvent(
                    node=str(node_name),
                    updates={"value": _jsonify(payload)},
                )
            )
    return events


def to_state_snapshot(snapshot: Any, *, thread_id: str) -> AgentStateSnapshot:
    next_nodes = list(snapshot.next) if getattr(snapshot, "next", None) else []
    tasks_out: list[AgentTaskSnapshot] = []
    for task in getattr(snapshot, "tasks", None) or ():
        interrupts = [
            {"value": _jsonify(getattr(i, "value", i))}
            for i in (getattr(task, "interrupts", None) or [])
        ]
        tasks_out.append(
            AgentTaskSnapshot(
                id=str(getattr(task, "id", "")),
                name=str(getattr(task, "name", "")),
                interrupts=interrupts,
            )
        )
    return AgentStateSnapshot(
        thread_id=thread_id,
        interrupted=snapshot_is_paused(snapshot),
        next_nodes=next_nodes,
        tasks=tasks_out,
    )
