"""LangGraph checkpoint saver backed by PostgreSQL.

Uses the official langgraph-checkpoint-postgres package.
"""

from __future__ import annotations

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config.settings import get_settings


def build_postgres_saver() -> AsyncPostgresSaver:
    settings = get_settings()
    return AsyncPostgresSaver.from_conn_string(settings.get_database_sync_url())
