"""FastAPI application factory and entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import app_exception_handler, unhandled_exception_handler
from app.api.v1.routers import auth_router, chat_router, health_router, session_router, user_router
from app.core.config.settings import get_settings
from app.core.exceptions import AppException
from app.core.observability import setup_observability
from app.infrastructure.cache.redis_manager import close_redis
from app.infrastructure.database.postgres.bootstrap import ensure_database_exists


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    ensure_database_exists()
    setup_observability()
    yield
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    openapi_tags = [
        {
            "name": "Health",
            "description": "Service readiness and basic environment details for smoke checks.",
        },
        {
            "name": "Authentication",
            "description": "Account registration, login, token refresh, and profile lookup.",
        },
        {
            "name": "Sessions",
            "description": "Conversation session lifecycle management for authenticated users.",
        },
        {
            "name": "Users",
            "description": "User management endpoints for listing, updating, and deleting users.",
        },
        {
            "name": "Chat",
            "description": "Agent execution endpoints (single response or streaming events).",
        },
    ]

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        lifespan=lifespan,
        description=(
            "API for authentication, session management, and LangGraph-powered chat.\n\n"
            "Quick test flow:\n"
            "1) Register or login.\n"
            "2) Use the returned `access_token` in the `Authorize` button as `Bearer <token>`.\n"
            "3) Create a session.\n"
            "4) Call chat endpoints with that `session_id`."
        ),
        openapi_tags=openapi_tags,
        contact={"name": "API Support", "email": "support@example.com"},
    )

    # ── Middleware ────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ───────────────────────────────────────
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ── Routers ──────────────────────────────────────────────────
    api_prefix = "/api/v1"
    app.include_router(health_router.router, prefix=api_prefix)
    app.include_router(auth_router.router, prefix=api_prefix)
    app.include_router(user_router.router, prefix=api_prefix)
    app.include_router(session_router.router, prefix=api_prefix)
    app.include_router(chat_router.router, prefix=api_prefix)

    return app


app = create_app()
