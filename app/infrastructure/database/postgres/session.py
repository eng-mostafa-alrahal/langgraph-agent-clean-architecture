"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config.settings import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_settings = get_settings()

engine = create_async_engine(
    _settings.get_database_url(),
    pool_size=_settings.DB_POOL_SIZE,
    max_overflow=_settings.DB_MAX_OVERFLOW,
    pool_recycle=_settings.DB_POOL_RECYCLE,
    echo=_settings.DEBUG,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncSession:  # type: ignore[misc]
    async with async_session_factory() as session:
        yield session  # type: ignore[misc]
