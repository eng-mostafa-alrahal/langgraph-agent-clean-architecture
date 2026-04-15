"""Session repository contract — extends the generic IRepository."""

from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from app.shared.domain_models.session import Session
from app.shared.ports.base_repository import IRepository


class ISessionRepository(IRepository[Session]):
    @abstractmethod
    async def list_by_user(self, user_id: UUID) -> list[Session]: ...
