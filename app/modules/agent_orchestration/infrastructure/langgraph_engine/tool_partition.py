"""Assign registered LangChain tools to specialised sub-graphs (with selective sharing)."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from app.modules.agent_orchestration.domain import tool_bucket_policy
from app.modules.agent_orchestration.domain.tool_bucket import AgentToolBucket

BUILTIN_RESEARCH_TOOL_NAMES = frozenset({"rag_search", "web_search", "get_local_time"})


def _default_buckets(tool_name: str) -> frozenset[AgentToolBucket]:
    """Legacy behaviour: built-ins → researcher only; all others → workspace only."""
    if tool_name in BUILTIN_RESEARCH_TOOL_NAMES:
        return frozenset({AgentToolBucket.RESEARCHER})
    return frozenset({AgentToolBucket.WORKSPACE})


def buckets_for_tool(tool: BaseTool) -> frozenset[AgentToolBucket]:
    """Resolve which subgraph(s) may bind this tool."""
    overrides = tool_bucket_policy.TOOL_BUCKET_OVERRIDES
    if tool.name in overrides:
        return overrides[tool.name]
    return _default_buckets(tool.name)


def partition_tools_for_agents(tools: list[BaseTool]) -> tuple[list[BaseTool], list[BaseTool]]:
    """Split tools into researcher vs workspace lists.

    The same ``BaseTool`` instance may appear in **both** lists when its policy
    includes both :class:`AgentToolBucket` values (shared binding).

    Overrides: ``app.modules.agent_orchestration.domain.tool_bucket_policy``.
    """
    research: list[BaseTool] = []
    workspace: list[BaseTool] = []
    for tool in tools:
        buckets = buckets_for_tool(tool)
        if AgentToolBucket.RESEARCHER in buckets:
            research.append(tool)
        if AgentToolBucket.WORKSPACE in buckets:
            workspace.append(tool)
    return research, workspace
