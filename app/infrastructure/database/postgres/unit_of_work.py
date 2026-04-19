"""Concrete Unit of Work backed by SQLAlchemy async sessions."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.postgres.repositories.session_repository import (
    SessionRepository,
)
from app.infrastructure.database.postgres.repositories.user_repository import UserRepository
from app.infrastructure.database.postgres.session import async_session_factory
from app.shared.ports.unit_of_work import IUnitOfWork


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(self) -> None:
        self._session_factory = async_session_factory

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self.session: AsyncSession = self._session_factory()
        self.users = UserRepository(self.session)
        self.sessions = SessionRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        if exc_type:
            await self.rollback()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
