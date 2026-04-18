"""Assign registered LangChain tools to specialised sub-agents."""

from __future__ import annotations

from langchain_core.tools import BaseTool

BUILTIN_RESEARCH_TOOL_NAMES = frozenset({"rag_search", "web_search", "get_local_time"})


def partition_tools_for_agents(tools: list[BaseTool]) -> tuple[list[BaseTool], list[BaseTool]]:
    """Split tools into researcher vs workspace (extended) tools.

    Built-in names (see ``dependencies._build_tool_registry``): ``rag_search``, ``web_search``,
    ``get_local_time`` go to the researcher. All other registered tools (typically MCP, and
    any future non-research integrations) are bound only to the workspace subgraph.
    """
    research: list[BaseTool] = []
    workspace: list[BaseTool] = []
    for tool in tools:
        if tool.name in BUILTIN_RESEARCH_TOOL_NAMES:
            research.append(tool)
        else:
            workspace.append(tool)
    return research, workspace
