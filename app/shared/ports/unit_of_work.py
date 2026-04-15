"""Unit of Work contract — coordinates transactional consistency."""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType


class IUnitOfWork(ABC):
    @abstractmethod
    async def __aenter__(self) -> IUnitOfWork: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
