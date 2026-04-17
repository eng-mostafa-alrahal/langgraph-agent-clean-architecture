"""Concrete user repository backed by PostgreSQL."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.postgres.models.user_model import UserORM
from app.modules.users.domain.user import User
from app.modules.users.ports.user_repository_port import IUserRepository


class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Mapping helpers ──────────────────────────────────────────
    @staticmethod
    def _to_domain(orm: UserORM) -> User:
        return User.model_validate(orm)

    @staticmethod
    def _to_orm(entity: User) -> UserORM:
        return UserORM(
            id=entity.id,
            name=entity.name,
            email=entity.email,
            hashed_password=entity.hashed_password,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    # ── CRUD ─────────────────────────────────────────────────────
    async def get_by_id(self, entity_id: UUID) -> User | None:
        orm = await self._session.get(UserORM, entity_id)
        return self._to_domain(orm) if orm else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserORM).where(UserORM.email == email)
        orm = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_all(self) -> list[User]:
        stmt = select(UserORM).order_by(UserORM.created_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    async def add(self, entity: User) -> User:
        orm = self._to_orm(entity)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def update(self, entity: User) -> User:
        orm = await self._session.get(UserORM, entity.id)
        if orm is None:
            raise ValueError(f"User {entity.id} not found")
        orm.name = entity.name
        orm.email = entity.email
        orm.hashed_password = entity.hashed_password
        orm.is_active = entity.is_active
        await self._session.flush()
        return self._to_domain(orm)

    async def delete(self, entity_id: UUID) -> None:
        orm = await self._session.get(UserORM, entity_id)
        if orm:
            await self._session.delete(orm)
            await self._session.flush()
