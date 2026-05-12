# LangGraph Agent - Clean Architecture

Production-oriented FastAPI + LangGraph backend structured with Clean Architecture and vertical modules.  
The system provides authenticated chat sessions, agent orchestration, optional human-in-the-loop approval, and pluggable tools (built-in + MCP).

> **Full project documentation lives in [`docs/`](./docs/README.md)** — architecture, request flow, agent orchestration internals, API reference, configuration, data model, tools, deployment, and testing.
>
> **New here?** Start with [`docs/onboarding.md`](./docs/onboarding.md) — the comprehensive new‑developer guide.

## What This Project Includes

- FastAPI API under `/api/v1` with auth, user, session, chat, and run-state endpoints
- LangGraph-based orchestrator in `app/modules/agent_orchestration`
- SQLAlchemy async persistence (PostgreSQL), Alembic migrations, Redis, JWT auth
- Optional Celery worker path for deferred/background graph execution
- MCP tool bootstrap at app startup with tool collision protection
- Unit/integration test suite and CI-friendly local scripts

## Architecture Overview

```text
app/
├── api/               HTTP delivery layer (routers, request/response schemas, dependencies)
├── core/              Global config, exceptions, security, observability, DI setup
├── infrastructure/    Shared adapters (database, cache, LLM/MCP gateways)
├── modules/
│   ├── users/                 User use-cases + domain logic
│   ├── sessions/              Session lifecycle use-cases
│   └── agent_orchestration/   LangGraph domain/application/infrastructure layers
└── shared/            Cross-module domain primitives and port contracts

workers/               Celery app and background task entrypoints
alembic/               Database migrations
hooks/                 Git hook scripts
scripts/               Developer startup and dependency sync scripts
tests/                 Unit, integration, and e2e tests
```

## Request Flow (High Level)

1. API router validates request DTOs.
2. FastAPI dependencies resolve use-cases and current user from JWT bearer token.
3. Use-case invokes the orchestrator or service layer through ports.
4. Infrastructure adapters execute DB, tool, LLM, and MCP interactions.
5. Response DTO is returned (or SSE stream for `/chat/stream`).

## Tech Stack

| Area | Main Libraries |
|---|---|
| API | FastAPI, Uvicorn |
| Agent orchestration | LangGraph, LangChain Core |
| LLM providers | OpenAI, Anthropic, Gemini adapters |
| Persistence | SQLAlchemy 2.0 (async), asyncpg, Alembic |
| Search/RAG extras | pgvector, langchain-postgres, Tavily |
| Auth | PyJWT, passlib/bcrypt |
| Caching/queue | Redis, Celery |
| Observability | OpenTelemetry, LangSmith |
| Tooling | uv, pytest, ruff, mypy |

## Quick Start

### 1) Start infrastructure

```bash
docker-compose up -d postgres redis
```

### 2) Create + activate virtual env

```bash
uv venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3) Install dependencies

```bash
uv sync --extra dev
```

### 4) Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set secrets/keys as needed.

### 5) Apply migrations

```bash
alembic upgrade head
```

### 6) Run API server

```bash
# Windows (PowerShell)
./scripts/dev.ps1

# macOS/Linux
./scripts/dev.sh
```

OpenAPI docs: `http://localhost:8000/docs`

### 7) Run tests

```bash
pytest -v
```

### 8) Optional: start Celery worker

```bash
celery -A workers.celery_app worker --loglevel=info --concurrency=2
```

## API Surface

All routes are prefixed with `/api/v1`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check and service metadata |
| `POST` | `/auth/register` | Register account |
| `POST` | `/auth/login` | Login and obtain access/refresh tokens |
| `POST` | `/auth/refresh` | Rotate refresh token and issue new pair |
| `GET` | `/auth/me` | Current authenticated profile |
| `GET` | `/users/` | List users (current-user scoped behavior) |
| `GET` | `/users/{user_id}` | Fetch one user |
| `PATCH` | `/users/{user_id}` | Update one user |
| `DELETE` | `/users/{user_id}` | Delete one user |
| `POST` | `/sessions/` | Create chat session |
| `GET` | `/sessions/` | List sessions |
| `GET` | `/sessions/{session_id}` | Get session details |
| `PATCH` | `/sessions/{session_id}` | Rename session |
| `DELETE` | `/sessions/{session_id}` | Delete session |
| `POST` | `/chat/` | Single-response chat invocation |
| `POST` | `/chat/stream` | SSE chat stream (`[DONE]` terminated) |
| `POST` | `/runs/{thread_id}/resume` | Resume interrupted run (human approval) |
| `GET` | `/runs/{thread_id}/state` | Inspect run state |

## Authentication Notes

- Use `Authorization: Bearer <access_token>` for protected routes.
- `GET /auth/me` is the quickest token validity check.
- User mutation endpoints enforce self-access constraints in the router layer.

## Configuration Reference

Primary config lives in `app/core/config/settings.py` and is loaded from `.env`.  
This project intentionally prefers `.env` values over stale process-level environment values.

### Important environment variables

- **App/runtime:** `APP_NAME`, `ENVIRONMENT`, `DEBUG`, `LOG_LEVEL`
- **Server:** `HOST`, `PORT`, `WORKERS`
- **Database:** `DATABASE_*`, `DATABASE_URL`, pool tuning vars
- **Redis/Celery:** `REDIS_*`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- **Auth:** `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- **LLM:** `DEFAULT_LLM_PROVIDER`, `DEFAULT_MODEL_NAME`, provider API keys
- **Agent limits:** `AGENT_MAX_CONTEXT_TOKENS`, `MAX_TOOL_OUTPUT_CHARS`, memory-summary vars
- **Research:** `TAVILY_API_KEY`, `PGVECTOR_ENABLED`, embedding/vector vars
- **MCP:** `MCP_SERVERS` (JSON array of server specs)

## MCP Integration

MCP tools are discovered at startup and injected into the shared tool registry.  
Name collisions between MCP tools and built-ins are blocked at boot.

- Supported transport types: `stdio`, `streamable_http`, `sse`
- Server definitions are configured via `MCP_SERVERS` in `.env`
- Filesystem MCP should be sandboxed to a dedicated directory like `mcp_workspace`

Detailed guide: `docs/architecture/mcp_integration.md`

## Developer Workflow

### VS Code / Cursor startup task

`.vscode/tasks.json` runs dependency sync on folder open (`scripts/sync_deps.ps1` / `.sh`).

### Git hooks

`hooks/pre-commit` keeps dependencies and `requirements.txt` synchronized before commit.

Enable once per clone:

```bash
git config --local core.hooksPath hooks
```

## Testing

- **Unit tests:** `tests/unit`
- **Integration tests:** `tests/integration`
- **E2E:** `tests/e2e` (chat e2e test is intentionally skipped unless full stack + keys are configured)

Run all:

```bash
pytest -v
```

## Project Principles

- Dependency rule: inner layers do not import outer layers
- Ports/adapters boundary around I/O
- Vertical module ownership (`users`, `sessions`, `agent_orchestration`)
- Pure domain logic with minimal framework coupling
- Explicit use-case orchestration and UoW-based data consistency

## Open Source

This repository is open source under the MIT License. See `LICENSE`.

## Contributing

Contributions are welcome. Please read `CONTRIBUTING.md` before opening a pull request.

## Security

Please report vulnerabilities according to `SECURITY.md` and do not open public issues for sensitive security findings.
