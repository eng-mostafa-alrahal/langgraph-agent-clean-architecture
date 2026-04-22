# Testing

How the test suite is laid out and how to run it.

## Layout

```text
tests/
├─ conftest.py              # shared fixtures (settings, app factory, auth helpers)
├─ unit/                    # pure, fast, no network
├─ integration/             # FastAPI TestClient / real DB
└─ e2e/                     # end-to-end (LLM calls, full stack)
```

All tests run under **`pytest-asyncio`** with `asyncio_mode = "auto"` (see `pyproject.toml`).

```bash
pytest -v
```

## Unit tests

Small, deterministic, no I/O. Cover the pure-domain surface and infrastructure helpers.

| File | Covers |
|---|---|
| `test_routing_rules.py` | Supervisor / researcher / approval routers |
| `test_memory_policy.py` | `should_summarize_messages` thresholds |
| `test_schema_compact.py` | Prompt schema compaction helpers |
| `test_message_snippets.py` | Internal message trimming utilities |
| `test_tool_partition.py` | Bucketing tools between researcher / workspace |
| `test_tool_execution_policy.py` | Tool error handling + output caps |
| `test_file_prompt_registry.py` | `FilePromptRegistry` reads TOML + Jinja correctly |
| `test_mcp_path_normalize.py` | Filesystem MCP path sandbox rules |
| `test_mcp_bootstrap.py` | MCP tool loading + collision detection |
| `test_internal_summary_filtering.py` | `is_internal_memory_summary_message` logic |
| `test_domain_models.py` | User / Session domain entity invariants |
| `test_jwt_service.py` | Token issue / verify / expiry |
| `test_exceptions.py` | `AppException` tree + serialisation |

Run just unit:

```bash
pytest tests/unit -v
```

## Integration tests

Exercise the real FastAPI app against a real Postgres (or `aiosqlite` when configured).

| File | Covers |
|---|---|
| `test_health.py` | `GET /health` returns 200 + expected shape |
| `test_auth_flow.py` | Register → login → `/auth/me` → refresh |

These run against whatever `DATABASE_URL` is active. Typical dev setup:

```bash
docker-compose up -d postgres redis
alembic upgrade head
pytest tests/integration -v
```

## End-to-end

`tests/e2e/test_chat_e2e.py` drives the full flow: register → create session → chat → expect a reply. It is **skipped by default** unless real LLM keys + infrastructure are present (it calls real LLMs and real tools). Opt in with:

```bash
export RUN_E2E=1
export OPENAI_API_KEY=sk-...   # or ANTHROPIC / GOOGLE
pytest tests/e2e -v
```

## Conventions

- **AAA** (Arrange / Act / Assert) comments are fine but not required.
- **No mocks at the domain layer.** Domain is pure — give it data, assert on the result.
- **Mock at the port.** When a use case needs an orchestrator / registry, build a `FakeOrchestrator` that implements `IAgentOrchestrator` and feeds the use case. See `tests/unit/*` for examples.
- **Freezable `datetime` / `uuid`.** Tests that care about IDs or timestamps inject a clock / id-generator, not `unittest.mock.patch` on `datetime.now`.
- **One behaviour per test.** Multiple asserts are fine as long as they describe a single outcome.
- **File naming.** Mirror the module path: `app/modules/users/domain/user.py` ↔ `tests/unit/test_domain_models.py` (consolidated) or a file-specific test.

## Linting + types

Match what CI expects:

```bash
ruff check .
ruff format --check .
mypy app
```

Tests aren't strictly typed (`mypy` scope = `app`), but prefer type annotations in fixtures for self-documentation.

## Coverage

```bash
pytest --cov=app --cov-report=term-missing
```

Aim for:

- ≥ 90% on `modules/*/domain/` (pure logic, easy to cover).
- ≥ 70% on `modules/*/application/` and `infrastructure/registries/`.
- Infrastructure adapters speaking to external services (LLM gateways, Postgres, MCP) are exercised by integration tests; low unit-test coverage on them is expected.

## Useful flags

```bash
pytest -k routing            # only tests matching "routing"
pytest -x                    # stop on first failure
pytest --lf                  # last failed
pytest -s                    # show print() + live logs
pytest -o log_cli=true -v    # live log output
```

## Adding a new test

For a new vertical feature, add:

1. A unit test per domain rule / policy.
2. A unit test for each use case, mocking the ports.
3. An integration test for the happy path end-to-end via FastAPI.
4. (Optional) An e2e test guarded by `RUN_E2E=1`.

## Git hook

`hooks/pre-commit` keeps `requirements.txt` synced with `pyproject.toml`. Enable once per clone:

```bash
git config --local core.hooksPath hooks
```

See `CONTRIBUTING.md` for the full quality-check checklist (`ruff`, `mypy`, `pytest`).
