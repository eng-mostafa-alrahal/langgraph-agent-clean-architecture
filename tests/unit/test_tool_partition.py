"""Tests for tool bucket partitioning."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.agent_orchestration.domain.tool_bucket import AgentToolBucket
from app.modules.agent_orchestration.infrastructure.langgraph_engine import tool_partition
from app.modules.agent_orchestration.infrastructure.langgraph_engine.tool_partition import (
    buckets_for_tool,
    partition_tools_for_agents,
)


def _mock_tool(name: str) -> MagicMock:
    t = MagicMock(spec=["name"])
    t.name = name
    return t


def test_default_builtin_goes_to_researcher_only() -> None:
    tools = [_mock_tool("rag_search"), _mock_tool("web_search"), _mock_tool("get_local_time")]
    research, workspace = partition_tools_for_agents(tools)
    assert len(research) == 3
    assert workspace == []


def test_default_unknown_goes_to_workspace_only() -> None:
    tools = [_mock_tool("filesystem__read")]
    research, workspace = partition_tools_for_agents(tools)
    assert research == []
    assert len(workspace) == 1


def test_override_can_share_tool_across_buckets(monkeypatch) -> None:
    monkeypatch.setattr(
        tool_partition.tool_bucket_policy,
        "TOOL_BUCKET_OVERRIDES",
        {"get_local_time": frozenset({AgentToolBucket.RESEARCHER, AgentToolBucket.WORKSPACE})},
    )
    t = _mock_tool("get_local_time")
    research, workspace = partition_tools_for_agents([t])
    assert research == [t]
    assert workspace == [t]
    assert buckets_for_tool(t) == frozenset({AgentToolBucket.RESEARCHER, AgentToolBucket.WORKSPACE})
