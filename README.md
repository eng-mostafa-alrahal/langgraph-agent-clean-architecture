# LangGraph Agent — Clean Architecture

Production-ready AI agent system combining **Clean Architecture** principles with **LangGraph** for sophisticated multi-agent orchestration.

## Architecture Overview

```
app/
├── core/              Cross-cutting concerns (config, security, exceptions, observability)
├── shared/            Enterprise kernel (domain models, port interfaces)
├── modules/
│   ├── users/         User management (register, login, profile)
│   ├── sessions/      Chat session lifecycle
│   └── agent_orchestration/
│       ├── domain/          Pure state schemas, routing rules, structured outputs
│       ├── application/     Use-cases & port interfaces (LLM registry, tool registry)
│       └── infrastructure/  LangGraph engine, sub-graphs, registries, tools
├── infrastructure/    Global adapters (PostgreSQL, Redis, LLM gateways)
└── api/               FastAPI presentation layer (routers, schemas, dependencies)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI + Uvicorn |
| Agent framework | LangGraph + LangChain |
| Database | PostgreSQL (async via SQLAlchemy 2.0 + asyncpg) |
| Migrations | Alembic |
| Cache / Pub-Sub | Redis |
| Auth | JWT (PyJWT + passlib/bcrypt) |
| Background tasks | Celery |
| Observability | OpenTelemetry + LangSmith |
| Package manager | uv |

## Quick Start

### 1. Infrastructure

```bash
docker-compose up -d postgres redis
```

### 2. Virtual Environment

```bash
uv venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
uv pip install -e ".[dev]"
```

### 4. Environment Variables

```bash
cp .env .env.local   # edit .env with your keys
```

### 5. Database Migrations

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 6. Run the Server

```bash
uvicorn app.main:app --reload
```

API docs available at: `http://localhost:8000/docs`

### 7. Run Tests

```bash
pytest tests/unit -v
```

### 8. Celery Worker (optional)

```bash
celery -A workers.celery_app worker --loglevel=info
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/auth/register` | Register a new user |
| `POST` | `/api/v1/auth/login` | Login and get tokens |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |
| `GET` | `/api/v1/auth/me` | Get current user profile |
| `POST` | `/api/v1/sessions/` | Create a chat session |
| `GET` | `/api/v1/sessions/` | List user sessions |
| `GET` | `/api/v1/sessions/{id}` | Get session details |
| `PATCH` | `/api/v1/sessions/{id}` | Rename a session |
| `DELETE` | `/api/v1/sessions/{id}` | Delete a session |
| `POST` | `/api/v1/chat/` | Send a message (sync) |
| `POST` | `/api/v1/chat/stream` | Send a message (SSE stream) |

## Project Principles

- **Dependency Rule** — inner layers never import from outer layers
- **Ports & Adapters** — all I/O goes through abstract interfaces
- **Vertical Slices** — each module owns its ports, use-cases, and is independently testable
- **Pure Domain** — state schemas and routing rules contain zero I/O
- **Unit of Work** — transactional consistency across repository operations
