"""Session management use-cases: create, list, rename, delete."""

from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError
from app.modules.sessions.domain.session import Session
from app.shared.ports.unit_of_work import IUnitOfWork


class SessionService:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    async def create_session(self, user_id: UUID, title: str = "New Chat") -> Session:
        async with self._uow as uow:
            session = Session(user_id=user_id, title=title)
            created = await uow.sessions.add(session)  # type: ignore[attr-defined]
            await uow.commit()
            return created

    async def list_sessions(self, user_id: UUID) -> list[Session]:
        async with self._uow as uow:
            return await uow.sessions.list_by_user(user_id)  # type: ignore[attr-defined]

    async def get_session(self, session_id: UUID, user_id: UUID) -> Session:
        async with self._uow as uow:
            session = await uow.sessions.get_by_id(session_id)  # type: ignore[attr-defined]
            if not session or session.user_id != user_id:
                raise NotFoundError("Session", str(session_id))
            return session

    async def rename_session(self, session_id: UUID, user_id: UUID, title: str) -> Session:
        async with self._uow as uow:
            session = await uow.sessions.get_by_id(session_id)  # type: ignore[attr-defined]
            if not session or session.user_id != user_id:
                raise NotFoundError("Session", str(session_id))

            updated = session.model_copy(update={"title": title})
            result = await uow.sessions.update(updated)  # type: ignore[attr-defined]
            await uow.commit()
            return result

    async def delete_session(self, session_id: UUID, user_id: UUID) -> None:
        async with self._uow as uow:
            session = await uow.sessions.get_by_id(session_id)  # type: ignore[attr-defined]
            if not session or session.user_id != user_id:
                raise NotFoundError("Session", str(session_id))
            await uow.sessions.delete(session_id)  # type: ignore[attr-defined]
            await uow.commit()
