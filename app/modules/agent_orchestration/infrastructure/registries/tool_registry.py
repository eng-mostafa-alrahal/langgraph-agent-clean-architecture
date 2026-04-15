"""Concrete tool registry — dynamically resolves LangChain tool instances."""

from __future__ import annotations

from langchain_core.tools import BaseTool

from app.modules.agent_orchestration.application.ports.tool_registry_port import IToolRegistry


class ToolRegistry(IToolRegistry):
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tools(self, tool_names: list[str]) -> list[BaseTool]:
        missing = set(tool_names) - set(self._tools)
        if missing:
            raise KeyError(f"Unknown tools: {missing}")
        return [self._tools[name] for name in tool_names]

    def list_available(self) -> list[str]:
        return list(self._tools.keys())
