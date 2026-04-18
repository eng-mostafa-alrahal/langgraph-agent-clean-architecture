# MCP client integration

This application can load external tools via the [Model Context Protocol](https://modelcontextprotocol.io/) **as a client**. MCP remains an infrastructure concern: LangChain tools are discovered at startup and registered in `ToolRegistry`, so domain code never imports MCP SDK types.

## Configuration

Define servers in `.env` as **`MCP_SERVERS`**, a JSON array of discriminated specs:

| `transport`        | Meaning |
|----------------------|---------|
| `stdio`              | Spawn a subprocess (recommended for `@modelcontextprotocol/server-filesystem`) |
| `streamable_http`    | Remote MCP over Streamable HTTP |
| `sse`                | Legacy SSE (deprecated upstream; emits a startup warning in logs) |

Example — official filesystem MCP via `npx`, rooted at `./mcp_workspace`:

```bash
MCP_SERVERS=[{"name":"filesystem","transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","mcp_workspace"]}]
```

Use an **absolute path** on your machine if you prefer (required if the working directory of the API process is not the repo root).

### Where files appear

The last argument to `@modelcontextprotocol/server-filesystem` is the **only directory** the MCP server may read or write. With the example above, all paths are confined to `./mcp_workspace` under the repo.

On disk, a successful `filesystem__write_file` with path `example.txt` ends up next to `.gitkeep` here:

`mcp_workspace/example.txt`

(or `mcp_workspace/subdir/example.txt` if you pass that relative path).

### Troubleshooting: “Access denied - path outside allowed directories”

That error means the resolved file path was **outside** the sandbox directory passed to `@modelcontextprotocol/server-filesystem`.

Common cause: the model supplies a bare filename like `example.txt`, which Python resolves relative to the API process **current working directory**, producing `<repo>\example.txt` instead of `<repo>\mcp_workspace\example.txt`.

This codebase installs a **LangChain MCP tool interceptor** (`FilesystemPathNormalizer`) that rewrites mistaken paths **before** the MCP server runs. Importantly, the MCP filesystem server resolves **relative** paths against its OS working directory (often the repo root). The interceptor therefore emits **absolute paths under `mcp_workspace`** (e.g. `<repo>\mcp_workspace\example.txt`) so writes cannot accidentally target `<repo>\example.txt`.

If you intentionally need the whole repo root as the writable tree, change the last argument from `mcp_workspace` to `.` (weakens isolation — only do this if you accept that risk).

## Tool naming

Tools from each server are registered as `server_name__original_tool_name` (double underscore), and descriptions are prefixed with `[server_name]` so the model knows which backend executed the call.

## Lifecycle

MCP tools are evaluated **once at application startup** (FastAPI lifespan). We intentionally do **not** subscribe to `notifications/tools/list_changed` at this time; to refresh external tools, restart the application. Revisit if a specific server's tool churn becomes operationally painful.

## Operational notes

- **Development + reload**: stdio transports spawn OS subprocess trees; `uvicorn --reload` can terminate workers abruptly and strand subprocesses on some platforms. Prefer a steady worker when exercising MCP heavily.
- **Checkpoint resume**: unknown tools are handled by LangGraph's `ToolNode` validation path; execution errors from MCP are converted into tool error messages for the LLM via `handle_tool_errors`.
