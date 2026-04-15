"""Verify JWT token creation and verification round-trips."""

from app.core.security.jwt_service import (
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
)
from app.shared.uuid_utils import uuid7


def test_access_token_roundtrip():
    uid = uuid7()
    token = create_access_token(uid)
    assert verify_access_token(token) == uid


def test_refresh_token_roundtrip():
    uid = uuid7()
    token = create_refresh_token(uid)
    assert verify_refresh_token(token) == uid
