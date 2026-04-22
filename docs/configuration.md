# Configuration

Everything is loaded from `.env` (via `pydantic-settings`). The schema is `app/core/config/settings.py`.

> **`.env` wins over OS env** — the source order is customised so that stale shell / IDE variables don't silently override the repo's `.env`. If a setting "looks ignored", it almost always means it's missing from `.env` and being picked up from your OS environment.

Re-read on every `get_settings()` call (no LRU cache), so editing `.env` and hitting a new request picks up the change without restart — except for values that only apply at graph-compile time. Those are listed under [Recompile-on-change](#recompile-on-change).

## Application

| Var | Type | Default | Notes |
|---|---|---|---|
| `APP_NAME` | str | `LangGraph Agent System` | Shown in OpenAPI + health. |
| `APP_VERSION` | str | `0.1.0` | — |
| `ENVIRONMENT` | `development` \| `staging` \| `production` | `development` | Changes logging behaviour + MCP warnings. |
| `DEBUG` | bool | `false` | Surfaces extra tracebacks in logs. |
| `LOG_LEVEL` | str | `INFO` | — |

## Server

| Var | Default | Notes |
|---|---|---|
| `HOST` | `0.0.0.0` | — |
| `PORT` | `8000` | — |
| `WORKERS` | `1` | Used by Gunicorn configs under `app/core/config/gunicorn_configs.py`. |

## Database (Postgres)

| Var | Default | Notes |
|---|---|---|
| `DATABASE_HOST` | `localhost` | — |
| `DATABASE_PORT` | `5432` | — |
| `DATABASE_USER` | `postgres` | — |
| `DATABASE_PASSWORD` | `postgres` | — |
| `DATABASE_NAME` | `agent_db` | Created automatically by `ensure_database_exists()` if missing. |
| `DATABASE_URL` | — | Full async URL. If set, overrides the components above. |
| `DB_POOL_SIZE` | `20` | SQLAlchemy pool. |
| `DB_MAX_OVERFLOW` | `10` | — |
| `DB_POOL_RECYCLE` | `3600` | Seconds. |

Built URL: `postgresql+asyncpg://<user>:<pw>@<host>:<port>/<db>`.  
A sync URL (`psycopg2`) is derived via `settings.get_database_sync_url()` for tools that need it (Alembic, LangGraph checkpointer).

## Redis

| Var | Default | Notes |
|---|---|---|
| `REDIS_HOST` | `localhost` | — |
| `REDIS_PORT` | `6379` | — |
| `REDIS_USER_NAME` | `default` | — |
| `REDIS_PASSWORD` | `` | — |
| `REDIS_DB` | `0` | — |
| `REDIS_SSL` | `true` | Set `false` for local dev. Selects `redis://` vs `rediss://`. |
| `REDIS_URL` | — | Full URL override. |

## JWT / Auth

| Var | Default | Notes |
|---|---|---|
| `JWT_SECRET_KEY` | `CHANGE-ME-IN-PRODUCTION` | **Must be set in any real deployment.** |
| `JWT_ALGORITHM` | `HS256` | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | — |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | — |
| `RATE_LIMIT_PER_MINUTE` | `60` | Used by `slowapi`. |

## LLM providers

| Var | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | `` | — |
| `ANTHROPIC_API_KEY` | `` | — |
| `GOOGLE_API_KEY` | `` | Gemini. |
| `DEFAULT_LLM_PROVIDER` | `openai` | One of `openai` \| `anthropic` \| `gemini`. |
| `DEFAULT_MODEL_NAME` | `openai/gpt-oss-120b` | Must be valid for the selected provider. |

Provider builders live in `app/infrastructure/llm_gateways/`.

## Research tools

| Var | Default | Notes |
|---|---|---|
| `TAVILY_API_KEY` | `` | If unset, `web_search` tool is not registered. Alias: `TAVILY_KEY`. |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Used by pgvector retriever. |
| `EMBEDDING_DIMENSIONS` | `1536` | Must match the embedding model. |
| `PGVECTOR_COLLECTION` | `knowledge_base` | Logical table namespace. |
| `PGVECTOR_ENABLED` | `false` | Requires the `pgvector` extension (the `pgvector/pgvector:pg16` image in `docker-compose.yml` has it). |

When `PGVECTOR_ENABLED=true` **and** `OPENAI_API_KEY` is set, the RAG tool is constructed with a live `pgvector` retriever.  If initialisation fails, a warning is logged and the tool registers with a disabled retriever — callers get a polite "no documents" message rather than an error.

## Observability

| Var | Default | Notes |
|---|---|---|
| `LANGSMITH_API_KEY` | `` | Enables LangSmith tracing when set. |
| `LANGSMITH_PROJECT` | `langgraph-agents` | — |
| `OTEL_EXPORTER_ENDPOINT` | `` | When set, OTel instrumentation is wired up (FastAPI auto-instrumentation). |

## MCP

| Var | Default | Notes |
|---|---|---|
| `MCP_SERVERS` | `[]` | JSON array of discriminated specs. See [`tools.md`](./tools.md#mcp) + [`architecture/mcp_integration.md`](./architecture/mcp_integration.md). |

Example (filesystem MCP via `npx`):

```bash
MCP_SERVERS=[{"name":"filesystem","transport":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-filesystem","mcp_workspace"]}]
```

## Prompts

| Var | Default | Notes |
|---|---|---|
| `PROMPT_ASSETS_DIR` | `app/modules/agent_orchestration/infrastructure/prompts` | Directory that contains intent subfolders. |
| `PROMPT_REGISTRY_PATH` | `app/core/config/prompt_registry.toml` | TOML mapping `intent → path`. |

Override both for Docker images that mount prompts as a volume.

## Agent limits & memory

| Var | Default | Notes |
|---|---|---|
| `AGENT_MAX_CONTEXT_TOKENS` | `12000` | Upper bound for per-subgraph prompt size (via `trim_messages`). Set `0` to disable trimming. |
| `SUPERVISOR_ROUTING_MAX_TOKENS` | `2048` | Tight cap for the routing step. |
| `MAX_TOOL_OUTPUT_CHARS` | `10000` | Truncates any single tool output before it re-enters the graph. Set `0` to disable. |
| `MEMORY_SUMMARIZATION_TRIGGER_MESSAGES` | `40` | If message count ≥ this, summarise. |
| `MEMORY_SUMMARIZATION_KEEP_RECENT_MESSAGES` | `12` | Keep the last N verbatim after summarising. |
| `MEMORY_SUMMARY_MAX_CHARS` | `4000` | Summary cap. |
| `MEMORY_SUMMARIZER_PROVIDER` | `` | If set, use a separate provider/model for memory summarisation (cheap model recommended). |
| `MEMORY_SUMMARIZER_MODEL_NAME` | `` | Required when `MEMORY_SUMMARIZER_PROVIDER` is set. |

## Celery

| Var | Default | Notes |
|---|---|---|
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | — |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | — |

## Recompile-on-change

Some settings only take effect when the compiled LangGraph is rebuilt. The orchestrator caches a signature of:

- `TAVILY_API_KEY`
- `PGVECTOR_ENABLED`
- `OPENAI_API_KEY` (bool)
- `DEFAULT_LLM_PROVIDER`
- `DEFAULT_MODEL_NAME`
- `AGENT_MAX_CONTEXT_TOKENS`
- `SUPERVISOR_ROUTING_MAX_TOKENS`
- `MAX_TOOL_OUTPUT_CHARS`
- `MEMORY_SUMMARIZATION_*`
- `MCP_SERVERS` (JSON-normalised)

When any of these change, the next request builds a fresh orchestrator with a new compiled graph. Other settings (log level, rate limits, CORS, etc.) apply immediately. MCP **tool bootstrap** is only performed at application startup — add/remove MCP servers requires an app restart.
