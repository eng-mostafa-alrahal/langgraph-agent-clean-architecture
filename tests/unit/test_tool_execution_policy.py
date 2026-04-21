"""Tests for bounded tool payloads (domain policy helpers)."""

from langchain_core.messages import ToolMessage
from langgraph.types import Command

from app.modules.agent_orchestration.domain.tool_execution_policy import truncate_tool_return
from app.modules.agent_orchestration.infrastructure.langgraph_engine.tool_output_cap import (
    tool_call_truncators,
)


def test_truncate_tool_return_short_unchanged() -> None:
    assert truncate_tool_return("ok", max_chars=100) == "ok"


def test_truncate_tool_return_inserts_notice() -> None:
    blob = "x" * 100
    out = truncate_tool_return(blob, max_chars=40)
    assert "[Truncated:" in out
    assert len(out) <= 40 + 80


def test_tool_call_truncators_noop_when_disabled() -> None:
    s, a = tool_call_truncators(0)
    assert s is None and a is None


def test_tool_call_truncators_truncates_tool_message_string() -> None:
    sync_w, async_w = tool_call_truncators(80)
    assert sync_w is not None and async_w is not None

    big = "y" * 200

    def execute(_request: object) -> ToolMessage:
        return ToolMessage(content=big, tool_call_id="t1")

    out = sync_w(None, execute)
    assert isinstance(out, ToolMessage)
    assert isinstance(out.content, str)
    assert len(out.content) < len(big)
    assert "Truncated" in out.content


def test_tool_call_truncators_passes_command_through() -> None:
    sync_w, _ = tool_call_truncators(50)
    assert sync_w is not None

    cmd = Command(update={"messages": []})

    def execute(_request: object) -> Command:
        return cmd

    assert sync_w(None, execute) is cmd
