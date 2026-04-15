"""Stateless JWT token creation and verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from app.core.config.settings import get_settings
from app.core.exceptions import InvalidTokenError, TokenExpiredError


def create_access_token(user_id: UUID, extra_claims: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError:
        raise InvalidTokenError()


def verify_access_token(token: str) -> UUID:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise InvalidTokenError()
    return UUID(payload["sub"])


def verify_refresh_token(token: str) -> UUID:
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise InvalidTokenError()
    return UUID(payload["sub"])
