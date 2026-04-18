"""Port for loading MCP-backed LangChain tools (infrastructure implements)."""

from __future__ import annotations

from typing import Protocol

from langchain_core.tools import BaseTool


class IMCPClient(Protocol):
    async def load_tools_by_server(self) -> dict[str, list[BaseTool]]:
        """Return MCP tools grouped by configured server ``name``."""

    async def aclose(self) -> None:
        """Release transports/subprocess handles where applicable."""
