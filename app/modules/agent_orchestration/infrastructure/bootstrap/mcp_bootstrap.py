"""Load MCP tools once at startup and normalize names for ``IToolRegistry``."""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool

from app.core.config.settings import get_settings
from app.core.exceptions import MCPBootstrapError
from app.infrastructure.mcp_gateways.path_interceptor import (
    get_stdio_sandbox_pair,
    wrap_mcp_tool_coroutine_paths,
)
from app.modules.agent_orchestration.application.ports.mcp_client_port import IMCPClient

logger = logging.getLogger(__name__)


def _namespaced_tool_name(server_name: str, tool_name: str) -> str:
    return f"{server_name}__{tool_name}"


async def bootstrap_mcp_tools(client: IMCPClient) -> list[BaseTool]:
    """Discover MCP tools, enforce ``server__tool`` uniqueness, enrich descriptions."""
    settings = get_settings()
    grouped = await client.load_tools_by_server()
    seen: set[str] = set()
    out: list[BaseTool] = []

    for server_name, tools in grouped.items():
        sandbox_pair = get_stdio_sandbox_pair(settings, server_name)
        for tool in tools:
            new_name = _namespaced_tool_name(server_name, tool.name)
            if new_name in seen:
                raise MCPBootstrapError(
                    detail=(
                        f"MCP tool name collision after namespacing: '{new_name}'. "
                        "Adjust MCP server configuration or tool names."
                    ),
                )
            seen.add(new_name)

            description = (tool.description or "").strip()
            prefixed = f"[{server_name}] {description}".strip()

            renamed = tool.model_copy(update={"name": new_name, "description": prefixed})
            if sandbox_pair is not None:
                sb, pr = sandbox_pair
                renamed = wrap_mcp_tool_coroutine_paths(renamed, sandbox_root=sb, project_root=pr)
            out.append(renamed)

    logger.info("MCP bootstrap registered %d tool(s) from %d server(s)", len(out), len(grouped))
    return out
