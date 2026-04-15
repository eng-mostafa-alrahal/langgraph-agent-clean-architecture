"""Verify the custom exception hierarchy."""

from app.core.exceptions import (
    AlreadyExistsError,
    AppException,
    AuthenticationError,
    InvalidCredentialsError,
    NotFoundError,
    RateLimitExceededError,
    TokenExpiredError,
    ValidationError,
)


def test_app_exception_defaults():
    exc = AppException()
    assert exc.status_code == 500
    assert exc.code == "APP_ERROR"


def test_not_found_with_identifier():
    exc = NotFoundError("User", "abc-123")
    assert "abc-123" in exc.detail
    assert exc.status_code == 404


def test_already_exists():
    exc = AlreadyExistsError("User", "test@example.com")
    assert exc.status_code == 409
    assert "test@example.com" in exc.detail


def test_authentication_hierarchy():
    assert issubclass(InvalidCredentialsError, AuthenticationError)
    assert issubclass(TokenExpiredError, AuthenticationError)
    assert InvalidCredentialsError().status_code == 401


def test_rate_limit():
    exc = RateLimitExceededError()
    assert exc.status_code == 429


def test_validation_error():
    exc = ValidationError("bad input")
    assert exc.status_code == 422
    assert exc.detail == "bad input"
