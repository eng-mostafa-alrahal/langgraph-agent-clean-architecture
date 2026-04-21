"""Intercept ToolNode executions and cap payload size before ToolMessages hit graph state."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import AsyncToolCallWrapper, ToolCallWrapper
from langgraph.types import Command

from app.modules.agent_orchestration.domain.tool_execution_policy import truncate_tool_return


def _truncate_tool_execution_result(result: ToolMessage | Command | Any, max_chars: int) -> Any:
    """Narrow oversized successful tool payloads; passes Commands through unchanged."""
    if max_chars <= 0:
        return result
    if isinstance(result, Command):
        return result
    if not isinstance(result, ToolMessage):
        return result

    raw = result.content
    if isinstance(raw, str):
        payload = truncate_tool_return(raw, max_chars)
        return result if payload == raw else result.model_copy(update={"content": payload})

    serialised = json.dumps(raw, ensure_ascii=False, default=str)
    payload = truncate_tool_return(serialised, max_chars)
    return result.model_copy(update={"content": payload})


def tool_call_truncators(
    max_chars: int,
) -> tuple[ToolCallWrapper | None, AsyncToolCallWrapper | None]:
    """Build LangGraph ToolNode wrappers that enforce :func:`truncate_tool_return`.

    Returns ``(None, None)`` when disabled so callers can omit wrapper kwargs.
    """
    if max_chars <= 0:
        return None, None

    def sync_wrap(request: Any, execute: Any) -> Any:
        out = execute(request)
        return _truncate_tool_execution_result(out, max_chars)

    async def async_wrap(request: Any, execute: Any) -> Any:
        out = await execute(request)
        return _truncate_tool_execution_result(out, max_chars)

    return sync_wrap, async_wrap
