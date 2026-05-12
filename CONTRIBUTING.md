> **First time in this repo?** Read [`docs/onboarding.md`](./docs/onboarding.md) before opening a PR. It covers the mental model, the dependency rule, where things live, and the recipes for common changes.

# Contributing

Thanks for your interest in contributing.

## Development setup

1. Fork and clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
uv sync --extra dev
```

4. Copy environment template:

```bash
cp .env.example .env
```

5. Start infrastructure and run migrations:

```bash
docker-compose up -d postgres redis
alembic upgrade head
```

## Branching and commits

- Create feature branches from `main`.
- Keep pull requests focused and small when possible.
- Write clear commit messages describing intent.

## Quality checks

Before opening a PR, run:

```bash
ruff check .
mypy app
pytest -v
```

## Pull request checklist

- Tests added or updated for behavior changes.
- Documentation updated when API or workflow changes.
- No secrets or local credentials committed.
- CI is green.
