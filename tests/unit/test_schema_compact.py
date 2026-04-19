"""Tests for compact JSON-schema summaries used in prompts."""

from __future__ import annotations

from app.modules.agent_orchestration.domain.prompts.schema_compact import compact_schema_for_llm
from app.modules.agent_orchestration.domain.schemas.research_decision import (
    DelegationDecision,
    WorkspaceLoopDecision,
)


def test_compact_schema_lists_delegation_fields() -> None:
    text = compact_schema_for_llm(DelegationDecision)
    assert "next_agent" in text
    assert "reasoning" in text
    assert "required" in text.lower() or "optional" in text.lower()


def test_compact_schema_workspace_loop_decision() -> None:
    text = compact_schema_for_llm(WorkspaceLoopDecision)
    assert "needs_more_tool_calls" in text
