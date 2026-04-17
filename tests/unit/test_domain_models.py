"""Verify shared domain model creation and immutability."""

import pytest
from pydantic import ValidationError

from app.modules.sessions.domain.session import Session
from app.modules.users.domain.user import User
from app.shared.uuid_utils import uuid7


def test_user_creation():
    user = User(name="Alice", email="alice@example.com", hashed_password="hash123")
    assert user.name == "Alice"
    assert user.is_active is True


def test_user_frozen():
    user = User(name="Bob", email="bob@example.com", hashed_password="hash")
    with pytest.raises(ValidationError):
        user.name = "Charlie"  # type: ignore[misc]


def test_session_creation():
    uid = uuid7()
    session = Session(user_id=uid, title="My Chat")
    assert session.user_id == uid
    assert session.title == "My Chat"


def test_session_default_title():
    uid = uuid7()
    session = Session(user_id=uid)
    assert session.title == "New Chat"
