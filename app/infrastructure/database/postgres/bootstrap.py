"""Database bootstrap helpers for local development ergonomics."""

from __future__ import annotations

import logging

import psycopg
from psycopg import sql
from sqlalchemy.engine import URL, make_url

from app.core.config.settings import get_settings

logger = logging.getLogger(__name__)


def _get_admin_url(target_url: URL) -> URL:
    """Return a URL to the postgres maintenance DB on same host."""
    return target_url.set(database="postgres")


def ensure_database_exists() -> None:
    """Create the configured PostgreSQL database if it does not exist."""
    settings = get_settings()
    target_url = make_url(settings.get_database_sync_url())
    admin_url = _get_admin_url(target_url)
    database_name = target_url.database

    if not database_name:
        raise ValueError("Database name is missing from DATABASE_URL configuration.")

    admin_dsn = admin_url.render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
        if cur.fetchone() is not None:
            logger.info("Database '%s' already exists", database_name)
            return

        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
        logger.info("Created database '%s'", database_name)
