"""User repository contract — extends the generic IRepository."""

from __future__ import annotations

from abc import abstractmethod

from app.shared.domain_models.user import User
from app.shared.ports.base_repository import IRepository


class IUserRepository(IRepository[User]):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def list_all(self) -> list[User]: ...
