"""LangGraph checkpoint saver backed by PostgreSQL.

Uses ``AsyncPostgresSaver`` with a process-lifetime :class:`psycopg_pool.AsyncConnectionPool`.
``from_conn_string`` is an async context manager and cannot be stored as the saver; the pool
pattern matches LangGraph's expected :class:`~langgraph.checkpoint.base.BaseCheckpointSaver` API.

Call :func:`init_postgres_checkpoint_saver` during app startup and :func:`close_postgres_checkpoint_saver`
on shutdown.
"""

from __future__ import annotations

import logging

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config.settings import get_settings

logger = logging.getLogger(__name__)

_pool: AsyncConnectionPool | None = None
_saver: AsyncPostgresSaver | None = None


def get_postgres_saver() -> AsyncPostgresSaver:
    """Return the singleton saver after :func:`init_postgres_checkpoint_saver` or :func:`ensure_checkpointer_ready`."""
    if _saver is None:
        msg = (
            "Postgres checkpoint saver is not initialized. "
            "Call ensure_checkpointer_ready() before compiling the graph, or "
            "init_postgres_checkpoint_saver() at application startup."
        )
        raise RuntimeError(msg)
    return _saver


async def init_postgres_checkpoint_saver() -> None:
    """Open the pool, construct the saver, and run checkpoint table migrations."""
    global _pool, _saver  # noqa: PLW0603

    if _saver is not None:
        return

    settings = get_settings()
    conninfo = settings.get_database_sync_url()

    _pool = AsyncConnectionPool(
        conninfo,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=False,
        min_size=1,
        max_size=10,
    )
    await _pool.open(wait=True)
    _saver = AsyncPostgresSaver(conn=_pool)
    await _saver.setup()
    logger.info("Postgres LangGraph checkpoint saver initialized")


async def close_postgres_checkpoint_saver() -> None:
    """Close the checkpoint connection pool."""
    global _pool, _saver  # noqa: PLW0603

    if _pool is not None:
        await _pool.close()
    _pool = None
    _saver = None


async def ensure_checkpointer_ready() -> AsyncPostgresSaver:
    """Ensure the saver exists and checkpoint tables are ready (idempotent)."""
    if _saver is None:
        await init_postgres_checkpoint_saver()
    return get_postgres_saver()
