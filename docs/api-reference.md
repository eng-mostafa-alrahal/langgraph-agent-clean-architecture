# API Reference

All routes are prefixed with **`/api/v1`**.

Interactive OpenAPI docs: <http://localhost:8000/docs>.  
Alternative ReDoc: <http://localhost:8000/redoc>.

## Authentication

All routes except `/health` and `/auth/*` require a Bearer token:

```
Authorization: Bearer <access_token>
```

- Tokens are issued by `POST /auth/login`.
- Expiry: `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 min).
- Refresh via `POST /auth/refresh` with the refresh token to rotate the pair.

## Endpoints at a glance

| Method | Path | Tag | Auth |
|---|---|---|---|
| `GET`    | `/health` | Health | no |
| `POST`   | `/auth/register` | Authentication | no |
| `POST`   | `/auth/login` | Authentication | no |
| `POST`   | `/auth/refresh` | Authentication | no |
| `GET`    | `/auth/me` | Authentication | yes |
| `GET`    | `/users/` | Users | yes |
| `GET`    | `/users/{user_id}` | Users | yes (self-only) |
| `PATCH`  | `/users/{user_id}` | Users | yes (self-only) |
| `DELETE` | `/users/{user_id}` | Users | yes (self-only) |
| `POST`   | `/sessions/` | Sessions | yes |
| `GET`    | `/sessions/` | Sessions | yes |
| `GET`    | `/sessions/{session_id}` | Sessions | yes (owner) |
| `PATCH`  | `/sessions/{session_id}` | Sessions | yes (owner) |
| `DELETE` | `/sessions/{session_id}` | Sessions | yes (owner) |
| `POST`   | `/chat/` | Chat | yes |
| `POST`   | `/chat/stream` | Chat | yes |
| `POST`   | `/runs/{thread_id}/resume` | Human Approval | yes |
| `GET`    | `/runs/{thread_id}/state` | Human Approval | yes |

## Common headers

| Header | Meaning |
|---|---|
| `x-request-id` (in) | Client-supplied correlation ID. Echoed back on the response. |
| `x-request-id` (out) | Always present; generated if not supplied. |
| `x-process-time-ms` (out) | Server-side wall time for the request. |

## Health

### `GET /health`

```json
{
  "status": "healthy",
  "app": "LangGraph Agent System",
  "version": "0.1.0",
  "environment": "development"
}
```

## Authentication

### `POST /auth/register` → `201 UserResponse`

```json
{ "name": "Ada", "email": "ada@example.com", "password": "StrongPass123!" }
```

### `POST /auth/login` → `200 TokenResponse`

```json
{ "email": "ada@example.com", "password": "StrongPass123!" }
```

Response:

```json
{
  "access_token": "…",
  "refresh_token": "…",
  "token_type": "bearer"
}
```

### `POST /auth/refresh` → `200 TokenResponse`

```json
{ "refresh_token": "…" }
```

### `GET /auth/me` → `200 UserResponse`

Current user profile, resolved from the bearer token.

## Users

All user-scoped routes enforce **self-access**: `user_id` in the path must equal the authenticated user, else `403 InsufficientPermissionsError`.

- `GET /users/` — returns a list containing only the current user (preserved for forward compatibility).
- `GET /users/{user_id}` — single user.
- `PATCH /users/{user_id}` — partial update (`name`, `email`, `is_active`).
- `DELETE /users/{user_id}` — cascade-deletes the user and their sessions.

## Sessions

A session is the persistence handle for a LangGraph thread. One session ↔ one thread.

- `POST /sessions/` — create (`{ "title": "…" }`, title optional).
- `GET /sessions/` — list for the authenticated user.
- `GET /sessions/{session_id}` — fetch by ID (must be owner).
- `PATCH /sessions/{session_id}` — rename (`{ "title": "…" }`).
- `DELETE /sessions/{session_id}` — delete row; LangGraph checkpoint rows are retained (harmless).

## Chat

### `POST /chat/`

Single-response invocation.

Request:

```json
{
  "message": "Summarize this document in 5 bullets.",
  "session_id": "019d92bc-2c73-74e6-814a-b647e46f0bf5",
  "stream_detail": "content"
}
```

Response (`ChatResponse`):

```json
{
  "session_id": "019d92bc-2c73-74e6-814a-b647e46f0bf5",
  "reply": "Here are the 5 bullets: …",
  "interrupted": false,
  "thread_id": "019d92bc-2c73-74e6-814a-b647e46f0bf5",
  "approval_request": null
}
```

When the agent paused for human review:

```json
{
  "session_id": "…",
  "reply": "",
  "interrupted": true,
  "thread_id": "…",
  "approval_request": {
    "reason": "workspace tool requires approval",
    "data": { "tool": "filesystem__write_file", "args": { "…": "…" } }
  }
}
```

Use the returned `thread_id` with `/runs/{thread_id}/resume` to continue.

### `POST /chat/stream`

Server-Sent Events stream. Same request body as `/chat/`.

Response is `text/event-stream`. Each chunk is `data: <json>\n\n`. The stream terminates with:

```
data: [DONE]
```

**`stream_detail=content` (default)** — compact:

```
data: {"content":"Here are the 5 bullets:"}

data: {"content":"1) …"}

data: {"content":"2) …"}

data: [DONE]
```

Only emits a chunk when the latest AI message has non-empty text (internal memory-summary messages are filtered out).

**`stream_detail=full`** — full per-node `AgentEvent`:

```json
{
  "node": "researcher",
  "messages": [{"type":"ai","content":"...","tool_calls":[...]}],
  "updates": { "retrieved_context": ["…"] }
}
```

Emits one chunk per meaningful per-node update (skipped when the payload has no new content and no updates).

## Human Approval

### `POST /runs/{thread_id}/resume`

`thread_id` == `session_id` of the original run.

Request (`ResumeRequest`):

```json
{
  "action": "approved",
  "feedback": "Go ahead."
}
```

- `action` must be `"approved"` or `"rejected"`.
- `feedback` is optional free text (≤ 2 000 chars).

Response (`ResumeResponse`):

```json
{
  "thread_id": "…",
  "reply": "Done. I wrote the file and verified its contents.",
  "interrupted": false,
  "approval_request": null
}
```

If the run is **not paused**, the API returns `409 GraphNotInterruptedError`.

### `GET /runs/{thread_id}/state`

Read-only snapshot.

```json
{
  "thread_id": "…",
  "interrupted": true,
  "next_nodes": ["human_review"],
  "tasks": [
    { "id": "…", "name": "human_review", "interrupts": [{"value": {"…": "…"}}] }
  ]
}
```

## Error response shape

All `AppException` subclasses produce:

```json
{
  "error": {
    "type": "RateLimitExceededError",
    "detail": "LLM provider quota or rate limit exceeded. Please retry later…",
    "request_id": "…"
  }
}
```

| HTTP | Exception |
|---|---|
| 400 | `ValidationError` (Pydantic), `GraphNotInterruptedError` (409 in some builds) |
| 401 | `AuthenticationError` |
| 403 | `InsufficientPermissionsError` |
| 404 | `NotFoundError` subclasses (e.g. `UserNotFoundError`, `SessionNotFoundError`) |
| 409 | `GraphNotInterruptedError`, `EmailAlreadyExistsError` |
| 429 | `RateLimitExceededError` |
| 500 | `AgentExecutionError`, `GraphCompilationError`, `MCPBootstrapError`, unhandled |

Exact status codes are defined in `app/core/exceptions.py`.

## DTO quick reference

See `app/modules/agent_orchestration/application/dtos/agent_result.py`:

- `AgentMessage { type, content, id?, tool_calls?, model?, usage? }`
- `AgentRunResult { messages[], interrupted, thread_id?, approval_request? }` + `last_ai_reply` property
- `AgentEvent { node, messages[], updates{} }`
- `AgentStateSnapshot { thread_id, interrupted, next_nodes[], tasks[] }`
- `ApprovalRequest { reason?, data{} }`
