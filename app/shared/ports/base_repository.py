"""Generic repository contract — every module repository extends this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> T | None: ...

    @abstractmethod
    async def add(self, entity: T) -> T: ...

    @abstractmethod
    async def update(self, entity: T) -> T: ...

    @abstractmethod
    async def delete(self, entity_id: UUID) -> None: ...
