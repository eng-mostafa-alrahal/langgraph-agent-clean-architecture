"""MCP server configuration models (stdio, Streamable HTTP, legacy SSE)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class MCPStdioSpec(BaseModel):
    """Spawn an MCP server as a subprocess (local Node, Python, etc.)."""

    model_config = {"extra": "forbid"}

    name: str = Field(..., description="Stable key; used as ToolNode namespacing prefix.")
    transport: Literal["stdio"] = "stdio"
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] | None = None
    cwd: str | None = None


class MCPStreamableHttpSpec(BaseModel):
    """Remote MCP over Streamable HTTP (preferred for modern servers)."""

    model_config = {"extra": "forbid"}

    name: str
    transport: Literal["streamable_http"] = "streamable_http"
    url: str
    headers: dict[str, str] | None = None


class MCPSseSpec(BaseModel):
    """Legacy HTTP+SSE transport (deprecated in MCP; kept for compatibility)."""

    model_config = {"extra": "forbid"}

    name: str
    transport: Literal["sse"] = "sse"
    url: str
    headers: dict[str, str] | None = None


MCPServerSpec = Annotated[
    MCPStdioSpec | MCPStreamableHttpSpec | MCPSseSpec,
    Field(discriminator="transport"),
]
