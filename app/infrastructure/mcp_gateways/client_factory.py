"""Build LangChain MCP clients from application settings."""

from __future__ import annotations

import logging

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import Connection

from app.core.config.mcp_servers import (
    MCPServerSpec,
    MCPSseSpec,
    MCPStdioSpec,
    MCPStreamableHttpSpec,
)
from app.core.config.settings import Settings
from app.infrastructure.mcp_gateways.path_interceptor import build_stdio_filesystem_interceptors
from app.modules.agent_orchestration.application.ports.mcp_client_port import IMCPClient

logger = logging.getLogger(__name__)


def _warn_sse_deprecated(server_name: str) -> None:
    logger.warning(
        "MCP server '%s' is using the deprecated 'sse' transport. "
        "Consider migrating to 'streamable_http'.",
        server_name,
    )


def spec_to_connection(spec: MCPServerSpec) -> Connection:
    """Map application config to langchain-mcp-adapters ``Connection`` dict."""
    if isinstance(spec, MCPStdioSpec):
        conn: Connection = {
            "transport": "stdio",
            "command": spec.command,
            "args": list(spec.args),
        }
        if spec.env is not None:
            conn["env"] = spec.env
        if spec.cwd is not None:
            conn["cwd"] = spec.cwd
        return conn

    if isinstance(spec, MCPStreamableHttpSpec):
        conn = {
            "transport": "streamable_http",
            "url": spec.url,
        }
        if spec.headers is not None:
            conn["headers"] = spec.headers
        return conn

    if isinstance(spec, MCPSseSpec):
        _warn_sse_deprecated(spec.name)
        conn = {
            "transport": "sse",
            "url": spec.url,
        }
        if spec.headers is not None:
            conn["headers"] = spec.headers
        return conn

    msg = f"Unsupported MCP server spec: {type(spec).__name__}"
    raise TypeError(msg)


def build_connections(settings: Settings) -> dict[str, Connection]:
    """Translate ``settings.MCP_SERVERS`` into MultiServerMCPClient wiring."""
    out: dict[str, Connection] = {}
    for spec in settings.MCP_SERVERS:
        if spec.name in out:
            msg = f"Duplicate MCP server name in configuration: {spec.name}"
            raise ValueError(msg)
        out[spec.name] = spec_to_connection(spec)
    return out


class LangChainMCPClient(IMCPClient):
    """Thin adapter over :class:`MultiServerMCPClient`."""

    def __init__(
        self,
        connections: dict[str, Connection],
        *,
        tool_interceptors: list | None = None,
    ) -> None:
        self._client = MultiServerMCPClient(
            connections=connections,
            tool_interceptors=tool_interceptors or [],
        )

    async def load_tools_by_server(self) -> dict[str, list[BaseTool]]:
        grouped: dict[str, list[BaseTool]] = {}
        for server_name in self._client.connections:
            grouped[server_name] = await self._client.get_tools(server_name=server_name)
        return grouped

    async def aclose(self) -> None:
        # MultiServerMCPClient does not keep a long-lived stdio process for tool *definitions*;
        # subprocesses are scoped to session creation inside the MCP SDK. Keep a stable hook for
        # future resource tracking (HTTP clients, custom stdio wrappers, etc.).
        return None


class NullMCPClient(IMCPClient):
    """No-op client when MCP is disabled (empty server list)."""

    async def load_tools_by_server(self) -> dict[str, list[BaseTool]]:
        return {}

    async def aclose(self) -> None:
        return None


class MCPClientFactory:
    """Factory for MCP clients — keeps SDK types out of ``core`` and FastAPI."""

    @staticmethod
    def create(settings: Settings) -> IMCPClient:
        if not settings.MCP_SERVERS:
            return NullMCPClient()
        connections = build_connections(settings)
        interceptors = build_stdio_filesystem_interceptors(settings)
        return LangChainMCPClient(connections=connections, tool_interceptors=interceptors)
