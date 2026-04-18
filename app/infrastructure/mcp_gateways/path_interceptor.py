"""Rewrite mistaken filesystem MCP paths before they hit the MCP server."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

from app.core.config.mcp_servers import MCPStdioSpec
from app.core.config.settings import Settings

logger = logging.getLogger(__name__)

_PATH_ARG_KEYS = frozenset({
    "path",
    "source",
    "destination",
    "from_path",
    "to_path",
    "old_path",
    "new_path",
})


def _absolute_under_sandbox(sandbox_root: Path, *relative_parts: str) -> str:
    """Return an absolute filesystem path confined under ``sandbox_root``."""
    root = sandbox_root.resolve()
    candidate = root.joinpath(*relative_parts).resolve()
    candidate.relative_to(root)
    return str(candidate)


def normalize_path_string(raw: str, sandbox_root: Path, project_root: Path) -> str:
    """Rewrite paths to **absolute** locations inside ``sandbox_root``.

    The MCP filesystem server resolves *relative* paths against its process working
    directory (often the Git repo root). A bare ``example.txt`` therefore becomes
    ``<repo>\\example.txt``, which is outside ``mcp_workspace``. After normalization we always
    emit a concrete absolute path under the configured sandbox directory.
    """
    trimmed = raw.strip().strip('"').strip("'")
    sandbox_root = sandbox_root.resolve()
    project_root = project_root.resolve()

    try:
        p = Path(trimmed)
    except OSError:
        return raw

    if not p.is_absolute():
        rel = trimmed.replace("\\", "/").lstrip("/")
        rel_parts = tuple(part for part in Path(rel).parts if part not in {".", ""})
        try:
            return _absolute_under_sandbox(sandbox_root, *rel_parts)
        except ValueError:
            return raw

    rp = p.resolve()

    try:
        rel_sandbox = rp.relative_to(sandbox_root)
        return _absolute_under_sandbox(sandbox_root, *rel_sandbox.parts)
    except ValueError:
        pass

    try:
        rel_proj = rp.relative_to(project_root)
    except ValueError:
        return raw

    parts = rel_proj.parts
    if len(parts) == 1:
        try:
            return _absolute_under_sandbox(sandbox_root, parts[0])
        except ValueError:
            return raw

    if parts and parts[0] == sandbox_root.name:
        inner = tuple(parts[1:])
        try:
            return _absolute_under_sandbox(sandbox_root, *inner)
        except ValueError:
            return raw

    return raw


def normalize_mcp_tool_args(
    args: Mapping[str, Any],
    sandbox_root: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Return a shallow copy of ``args`` with filesystem paths rewritten where needed."""
    out = dict(args)

    def fix_value(key: str, val: Any) -> Any:
        if isinstance(val, str) and key in _PATH_ARG_KEYS:
            new_val = normalize_path_string(val, sandbox_root, project_root)
            if new_val != val:
                logger.debug(
                    "mcp.path_normalize key=%s before=%r after=%r sandbox=%s",
                    key,
                    val,
                    new_val,
                    sandbox_root,
                )
            return new_val
        if key == "paths" and isinstance(val, list):
            fixed = []
            changed = False
            for item in val:
                if isinstance(item, str):
                    nv = normalize_path_string(item, sandbox_root, project_root)
                    fixed.append(nv)
                    changed = changed or nv != item
                else:
                    fixed.append(item)
            return fixed if changed else val
        return val

    for key in list(out.keys()):
        out[key] = fix_value(key, out[key])

    return out


class FilesystemPathNormalizer:
    """Interceptor: adjusts ``path`` (and related) arguments for MCP filesystem servers."""

    def __init__(
        self,
        server_name: str,
        sandbox_root: Path,
        project_root: Path,
    ) -> None:
        self.server_name = server_name
        self.sandbox_root = sandbox_root
        self.project_root = project_root

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[Any]],
    ) -> Any:
        if request.server_name != self.server_name:
            return await handler(request)

        normalized = normalize_mcp_tool_args(
            request.args,
            self.sandbox_root,
            self.project_root,
        )
        req = request.override(args=normalized) if normalized != request.args else request
        return await handler(req)


def resolve_stdio_sandbox_directories(spec: MCPStdioSpec) -> tuple[Path, Path]:
    """Return ``(sandbox_root, project_root)`` from a stdio spec's last CLI argument."""
    if not spec.args:
        msg = "stdio MCP spec must include args ending with the sandbox directory"
        raise ValueError(msg)

    sandbox_raw = spec.args[-1]
    sandbox_path = Path(sandbox_raw)
    sandbox_root = (
        sandbox_path.resolve()
        if sandbox_path.is_absolute()
        else (Path.cwd() / sandbox_path).resolve()
    )
    project_root = sandbox_root.parent
    return sandbox_root, project_root


def get_stdio_sandbox_pair(settings: Settings, server_name: str) -> tuple[Path, Path] | None:
    """Resolve sandbox directories for a configured stdio MCP server name, if any."""
    for spec in settings.MCP_SERVERS:
        if isinstance(spec, MCPStdioSpec) and spec.name == server_name and spec.args:
            return resolve_stdio_sandbox_directories(spec)
    return None


def build_stdio_filesystem_interceptors(settings: Settings) -> list[FilesystemPathNormalizer]:
    """One normalizer per stdio server that passes a sandbox directory as the last CLI arg."""
    interceptors: list[FilesystemPathNormalizer] = []
    for spec in settings.MCP_SERVERS:
        if not isinstance(spec, MCPStdioSpec):
            continue
        if not spec.args:
            continue

        sandbox_root, project_root = resolve_stdio_sandbox_directories(spec)

        interceptors.append(
            FilesystemPathNormalizer(spec.name, sandbox_root, project_root),
        )

    return interceptors


def wrap_mcp_tool_coroutine_paths(
    tool: BaseTool,
    *,
    sandbox_root: Path,
    project_root: Path,
) -> BaseTool:
    """Wrap the LangChain tool coroutine so paths are normalized at invocation time.

    This duplicates the MCP adapter interceptor layer on purpose: some deployments
    have seen tool calls bypass the interceptor chain while still using the same
    StructuredTool coroutine; rewriting kwargs here is deterministic.
    """
    coroutine = getattr(tool, "coroutine", None)
    if coroutine is None:
        return tool

    async def normalized_coroutine(*args: Any, **kwargs: Any) -> Any:
        merged = normalize_mcp_tool_args(kwargs, sandbox_root, project_root)
        return await coroutine(*args, **merged)

    return tool.model_copy(update={"coroutine": normalized_coroutine})
