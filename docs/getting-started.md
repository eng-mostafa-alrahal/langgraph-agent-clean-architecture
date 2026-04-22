# Getting Started

Boot the API, run a chat, and make sure everything is wired correctly.

## 1. Prerequisites

- **Python 3.11+** (enforced in `pyproject.toml`)
- **Docker** (for Postgres + Redis via `docker-compose.yml`)
- **`uv`** package manager ([install](https://docs.astral.sh/uv/))
- **Node.js** (only if you plan to use stdio MCP servers like the filesystem MCP)
- At least one LLM provider API key (OpenAI, Anthropic, or Gemini)

## 2. Start infrastructure

```bash
docker-compose up -d postgres redis
```

This launches:

- `postgres` — `pgvector/pgvector:pg16` image on port `5432`
- `redis` — `redis:7-alpine` on port `6379`

## 3. Install dependencies

```bash
uv venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

uv sync --extra dev
```

## 4. Configure `.env`

```bash
cp .env.example .env
```

Open `.env` and set **at minimum**:

- `JWT_SECRET_KEY` — any long random string.
- `OPENAI_API_KEY` **or** `ANTHROPIC_API_KEY` **or** `GOOGLE_API_KEY`.
- `DEFAULT_LLM_PROVIDER` — must match the provider above (`openai` | `anthropic` | `gemini`).
- `DEFAULT_MODEL_NAME` — a model ID valid for that provider.

Everything else has sensible defaults. See [`configuration.md`](./configuration.md) for the full reference.

## 5. Apply migrations

```bash
alembic upgrade head
```

This creates the `users` and `sessions` tables. LangGraph's Postgres checkpointer provisions its own tables lazily on first run.

## 6. Run the API

```bash
# Windows (PowerShell)
./scripts/dev.ps1

# macOS / Linux
./scripts/dev.sh
```

Open <http://localhost:8000/docs> for the interactive OpenAPI UI.

## 7. First end-to-end chat

```bash
# 1) Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Ada","email":"ada@example.com","password":"hunter22"}'

# 2) Login and grab access_token from the response
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ada@example.com","password":"hunter22"}'

# 3) Create a session (replace $TOKEN)
curl -X POST http://localhost:8000/api/v1/sessions/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"first chat"}'

# 4) Chat (replace $SESSION_ID)
curl -X POST http://localhost:8000/api/v1/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"'$SESSION_ID'","message":"Hi, what time is it in Tokyo?"}'
```

If the final response includes `"interrupted": true`, the agent is waiting for human approval — see [`agent-orchestration.md`](./agent-orchestration.md#human-in-the-loop-hitl) and [`api-reference.md`](./api-reference.md#human-approval).

## 8. Run the tests

```bash
pytest -v
```

The e2e chat test is skipped by default unless the full stack + real API keys are present.

## 9. Optional: Celery worker

```bash
celery -A workers.celery_app worker --loglevel=info --concurrency=2
```

Use this path when you want agent runs deferred out of the HTTP request cycle. See [`deployment.md`](./deployment.md).

## Next steps

- Read [`architecture.md`](./architecture.md) to understand why the code is organised the way it is.
- Read [`agent-orchestration.md`](./agent-orchestration.md) to see how the LangGraph supervisor routes to specialist subgraphs.
- Read [`tools.md`](./tools.md) to add your own tool or plug in an MCP server.
