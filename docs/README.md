# Documentation

This directory is the canonical reference for how the **LangGraph Agent — Clean Architecture** project is organised, how requests flow through it, and how to run / extend it.

The docs are intentionally **high level**. For file-by-file detail, read the source alongside the matching doc page.

## Who this is for

- **OSS users** who want to install, configure, and call the API.
- **Contributors / maintainers** who want to understand the architecture and safely extend it.

## Quick map

| Topic | Start here |
|---|---|
| Install + run a first chat | [`getting-started.md`](./getting-started.md) |
| How the code is layered | [`architecture.md`](./architecture.md) |
| What happens on `POST /chat/` | [`request-flow.md`](./request-flow.md) |
| LangGraph supervisor / researcher / workspace | [`agent-orchestration.md`](./agent-orchestration.md) |
| All HTTP endpoints + SSE protocol | [`api-reference.md`](./api-reference.md) |
| All environment variables | [`configuration.md`](./configuration.md) |
| Database schema + checkpointer | [`data-model.md`](./data-model.md) |
| Built-in tools + MCP tools | [`tools.md`](./tools.md) |
| Docker, Celery, production | [`deployment.md`](./deployment.md) |
| Tests and how to run them | [`testing.md`](./testing.md) |
| Deep-dive: MCP wiring | [`architecture/mcp_integration.md`](./architecture/mcp_integration.md) |

## Reading order

If this is your first time in the repo, read in this order:

1. [`getting-started.md`](./getting-started.md) — get the API up.
2. [`architecture.md`](./architecture.md) — understand the layers and dependency rule.
3. [`request-flow.md`](./request-flow.md) — follow one request end-to-end.
4. [`agent-orchestration.md`](./agent-orchestration.md) — learn the LangGraph internals.
5. Pick any topic from the table above.

## Conventions

- All Python code lives under `app/` with a clean-architecture split (`api` → `modules` → `infrastructure` / `core` / `shared`).
- Diagrams use **Mermaid**; GitHub renders them natively.
- When this doc says "port", it means an interface under `.../application/ports/…` (dependency inversion boundary).
- When it says "adapter", it means a concrete implementation under `infrastructure/…` that fulfils a port.
