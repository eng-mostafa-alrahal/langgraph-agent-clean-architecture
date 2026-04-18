"""Unit tests for MCP bootstrap (namespacing / collisions)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from langchain_core.tools import StructuredTool

from app.core.exceptions import MCPBootstrapError
from app.modules.agent_orchestration.infrastructure.bootstrap.mcp_bootstrap import (
    bootstrap_mcp_tools,
)


def _make_tool(name: str, description: str = "") -> StructuredTool:
    def _noop(**_: object) -> str:
        return "ok"

    return StructuredTool.from_function(_noop, name=name, description=description)


@pytest.mark.asyncio
async def test_bootstrap_prefixes_tool_names_and_descriptions() -> None:
    client = AsyncMock()
    client.load_tools_by_server = AsyncMock(
        return_value={"filesystem": [_make_tool("write_file", "Writes text files.")]}
    )

    tools = await bootstrap_mcp_tools(client)

    assert len(tools) == 1
    assert tools[0].name == "filesystem__write_file"
    assert tools[0].description.startswith("[filesystem]")


@pytest.mark.asyncio
async def test_bootstrap_collision_is_fatal() -> None:
    client = AsyncMock()
    client.load_tools_by_server = AsyncMock(
        return_value={
            "filesystem": [_make_tool("same"), _make_tool("same")],
        }
    )

    with pytest.raises(MCPBootstrapError):
        await bootstrap_mcp_tools(client)
