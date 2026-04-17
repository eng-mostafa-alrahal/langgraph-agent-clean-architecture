"""Domain and application exception hierarchy.

All exceptions carry a machine-readable `code` so that the API layer can
map them to the correct HTTP status without inspecting message strings.
"""

from __future__ import annotations


# ── Base ─────────────────────────────────────────────────────────
class AppException(Exception):
    """Root for every custom exception in the system."""

    code: str = "APP_ERROR"
    status_code: int = 500

    def __init__(self, detail: str = "An unexpected error occurred.") -> None:
        self.detail = detail
        super().__init__(self.detail)


# ── Authentication / Authorisation ───────────────────────────────
class AuthenticationError(AppException):
    code = "AUTHENTICATION_ERROR"
    status_code = 401

    def __init__(self, detail: str = "Could not validate credentials.") -> None:
        super().__init__(detail)


class InvalidCredentialsError(AuthenticationError):
    code = "INVALID_CREDENTIALS"

    def __init__(self) -> None:
        super().__init__("Incorrect email or password.")


class TokenExpiredError(AuthenticationError):
    code = "TOKEN_EXPIRED"

    def __init__(self) -> None:
        super().__init__("Token has expired.")


class InvalidTokenError(AuthenticationError):
    code = "INVALID_TOKEN"

    def __init__(self) -> None:
        super().__init__("Token is invalid or malformed.")


class InsufficientPermissionsError(AppException):
    code = "FORBIDDEN"
    status_code = 403

    def __init__(self, detail: str = "You do not have permission.") -> None:
        super().__init__(detail)


# ── Resource errors ──────────────────────────────────────────────
class NotFoundError(AppException):
    code = "NOT_FOUND"
    status_code = 404

    def __init__(self, resource: str = "Resource", identifier: str = "") -> None:
        msg = f"{resource} not found." if not identifier else f"{resource} '{identifier}' not found."
        super().__init__(msg)


class AlreadyExistsError(AppException):
    code = "ALREADY_EXISTS"
    status_code = 409

    def __init__(self, resource: str = "Resource", identifier: str = "") -> None:
        msg = (
            f"{resource} already exists."
            if not identifier
            else f"{resource} '{identifier}' already exists."
        )
        super().__init__(msg)


# ── Validation ───────────────────────────────────────────────────
class ValidationError(AppException):
    code = "VALIDATION_ERROR"
    status_code = 422

    def __init__(self, detail: str = "Validation failed.") -> None:
        super().__init__(detail)


# ── Rate Limiting ────────────────────────────────────────────────
class RateLimitExceededError(AppException):
    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429

    def __init__(self, detail: str = "Rate limit exceeded. Try again later.") -> None:
        super().__init__(detail)


# ── Agent / LLM errors ──────────────────────────────────────────
class AgentExecutionError(AppException):
    code = "AGENT_EXECUTION_ERROR"
    status_code = 500

    def __init__(self, detail: str = "Agent execution failed.") -> None:
        super().__init__(detail)


class LLMProviderError(AppException):
    code = "LLM_PROVIDER_ERROR"
    status_code = 502

    def __init__(self, provider: str = "LLM", detail: str = "") -> None:
        msg = f"{provider} provider error." if not detail else f"{provider}: {detail}"
        super().__init__(msg)


class GraphCompilationError(AppException):
    code = "GRAPH_COMPILATION_ERROR"
    status_code = 500

    def __init__(self, detail: str = "Failed to compile the agent graph.") -> None:
        super().__init__(detail)


class GraphNotInterruptedError(AppException):
    code = "GRAPH_NOT_INTERRUPTED"
    status_code = 409

    def __init__(self, detail: str = "Graph run is not in an interrupted state.") -> None:
        super().__init__(detail)


# ── Infrastructure ───────────────────────────────────────────────
class DatabaseError(AppException):
    code = "DATABASE_ERROR"
    status_code = 500

    def __init__(self, detail: str = "A database error occurred.") -> None:
        super().__init__(detail)


class CacheError(AppException):
    code = "CACHE_ERROR"
    status_code = 500

    def __init__(self, detail: str = "A cache error occurred.") -> None:
        super().__init__(detail)


class ExternalServiceError(AppException):
    code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502

    def __init__(self, service: str = "External service", detail: str = "") -> None:
        msg = f"{service} is unavailable." if not detail else f"{service}: {detail}"
        super().__init__(msg)
