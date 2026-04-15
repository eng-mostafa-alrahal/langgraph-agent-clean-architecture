"""Concrete session repository backed by PostgreSQL."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.postgres.models.session_model import SessionORM
from app.modules.sessions.ports.session_repository_port import ISessionRepository
from app.shared.domain_models.session import Session


class SessionRepository(ISessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(orm: SessionORM) -> Session:
        return Session.model_validate(orm)

    @staticmethod
    def _to_orm(entity: Session) -> SessionORM:
        return SessionORM(
            id=entity.id,
            user_id=entity.user_id,
            title=entity.title,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def get_by_id(self, entity_id: UUID) -> Session | None:
        orm = await self._session.get(SessionORM, entity_id)
        return self._to_domain(orm) if orm else None

    async def list_by_user(self, user_id: UUID) -> list[Session]:
        stmt = (
            select(SessionORM)
            .where(SessionORM.user_id == user_id)
            .order_by(SessionORM.updated_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def add(self, entity: Session) -> Session:
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def update(self, entity: Session) -> Session:
        orm = await self._session.get(SessionORM, entity.id)
        if orm is None:
            raise ValueError(f"Session {entity.id} not found")
        orm.title = entity.title
        await self._session.flush()
        return self._to_domain(orm)

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(SessionORM, entity_id)
        if orm:
            await self._session.delete(orm)
            await self._session.flush()
