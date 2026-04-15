"""User management use-cases: register, authenticate, profile retrieval."""

from __future__ import annotations

import hashlib
from uuid import UUID

import bcrypt

from app.core.exceptions import AlreadyExistsError, InvalidCredentialsError, NotFoundError
from app.core.security.jwt_service import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.shared.domain_models.user import User
from app.shared.ports.unit_of_work import IUnitOfWork


def _prehash_password(password: str) -> bytes:
    """Normalize password length before bcrypt by SHA-256 pre-hashing."""
    return hashlib.sha256(password.encode("utf-8")).digest()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(
        _prehash_password(password),
        bcrypt.gensalt(),
    ).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        _prehash_password(password),
        password_hash.encode("utf-8"),
    )


class UserService:
    def __init__(self, uow: IUnitOfWork) -> None:
        self._uow = uow

    # ── Registration ─────────────────────────────────────────────
    async def register(self, name: str, email: str, password: str) -> User:
        async with self._uow as uow:
            existing = await uow.users.get_by_email(email)  # type: ignore[attr-defined]
            if existing:
                raise AlreadyExistsError("User", email)

            user = User(
                name=name,
                email=email,
                hashed_password=_hash_password(password),
            )
            created = await uow.users.add(user)  # type: ignore[attr-defined]
            await uow.commit()
            return created

    # ── Authentication ───────────────────────────────────────────
    async def authenticate(self, email: str, password: str) -> dict[str, str]:
        async with self._uow as uow:
            user = await uow.users.get_by_email(email)  # type: ignore[attr-defined]
            if not user or not _verify_password(password, user.hashed_password):
                raise InvalidCredentialsError()

            return {
                "access_token": create_access_token(user.id),
                "refresh_token": create_refresh_token(user.id),
                "token_type": "bearer",
            }

    # ── Token refresh ────────────────────────────────────────────
    async def refresh_tokens(self, refresh_token: str) -> dict[str, str]:
        user_id = verify_refresh_token(refresh_token)
        async with self._uow as uow:
            user = await uow.users.get_by_id(user_id)  # type: ignore[attr-defined]
            if not user:
                raise NotFoundError("User", str(user_id))

            return {
                "access_token": create_access_token(user.id),
                "refresh_token": create_refresh_token(user.id),
                "token_type": "bearer",
            }

    # ── Profile ──────────────────────────────────────────────────
    async def get_profile(self, user_id: UUID) -> User:
        async with self._uow as uow:
            user = await uow.users.get_by_id(user_id)  # type: ignore[attr-defined]
            if not user:
                raise NotFoundError("User", str(user_id))
            return user

    # ── Management ───────────────────────────────────────────────
    async def list_users(self) -> list[User]:
        async with self._uow as uow:
            return await uow.users.list_all()  # type: ignore[attr-defined]

    async def get_user(self, user_id: UUID) -> User:
        async with self._uow as uow:
            user = await uow.users.get_by_id(user_id)  # type: ignore[attr-defined]
            if not user:
                raise NotFoundError("User", str(user_id))
            return user

    async def update_user(
        self,
        user_id: UUID,
        *,
        name: str | None = None,
        email: str | None = None,
        is_active: bool | None = None,
    ) -> User:
        async with self._uow as uow:
            user = await uow.users.get_by_id(user_id)  # type: ignore[attr-defined]
            if not user:
                raise NotFoundError("User", str(user_id))

            if email and email != user.email:
                existing = await uow.users.get_by_email(email)  # type: ignore[attr-defined]
                if existing and existing.id != user_id:
                    raise AlreadyExistsError("User", email)

            updated = user.model_copy(
                update={
                    "name": name if name is not None else user.name,
                    "email": email if email is not None else user.email,
                    "is_active": is_active if is_active is not None else user.is_active,
                }
            )
            result = await uow.users.update(updated)  # type: ignore[attr-defined]
            await uow.commit()
            return result

    async def delete_user(self, user_id: UUID) -> None:
        async with self._uow as uow:
            user = await uow.users.get_by_id(user_id)  # type: ignore[attr-defined]
            if not user:
                raise NotFoundError("User", str(user_id))
            await uow.users.delete(user_id)  # type: ignore[attr-defined]
            await uow.commit()
