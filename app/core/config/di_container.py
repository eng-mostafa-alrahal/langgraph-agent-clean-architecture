"""Dependency Injection bootstrapping.

Wires together ports and adapters so that use-cases receive concrete
implementations at runtime without importing infrastructure directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.database.postgres.unit_of_work import SqlAlchemyUnitOfWork
    from app.modules.sessions.use_cases.session_service import SessionService
    from app.modules.users.use_cases.user_service import UserService


@dataclass(slots=True)
class DIContainer:
    """Simple IoC container — swap with dependency-injector if complexity grows."""

    _singletons: dict[str, object] = field(default_factory=dict, init=False)

    # ── Registration helpers ─────────────────────────────────────
    def register_singleton(self, key: str, instance: object) -> None:
        self._singletons[key] = instance

    def resolve(self, key: str) -> object:
        try:
            return self._singletons[key]
        except KeyError:
            raise LookupError(f"No registration found for '{key}'") from None

    # ── Typed accessors for common services ──────────────────────
    @property
    def uow(self) -> SqlAlchemyUnitOfWork:

        return self.resolve("uow")  # type: ignore[return-value]

    @property
    def user_service(self) -> UserService:

        return self.resolve("user_service")  # type: ignore[return-value]

    @property
    def session_service(self) -> SessionService:

        return self.resolve("session_service")  # type: ignore[return-value]


_container: DIContainer | None = None


def get_container() -> DIContainer:
    global _container
    if _container is None:
        _container = DIContainer()
    return _container
