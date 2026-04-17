"""FastAPI application factory and entry point."""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

# Psycopg async (LangGraph Postgres checkpointer) requires a selector loop on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import app_exception_handler, unhandled_exception_handler
from app.api.v1.routers import (
    auth_router,
    chat_router,
    health_router,
    human_approval_router,
    session_router,
    user_router,
)
from app.core.config.settings import get_settings
from app.core.exceptions import AppException
from app.core.observability import setup_observability
from app.core.observability.request_context import set_request_id
from app.infrastructure.cache.redis_manager import close_redis
from app.infrastructure.database.postgres.bootstrap import ensure_database_exists
from app.modules.agent_orchestration.infrastructure.langgraph_engine.memory.postgres_saver import (
    close_postgres_checkpoint_saver,
    init_postgres_checkpoint_saver,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    ensure_database_exists()
    await init_postgres_checkpoint_saver()
    setup_observability()
    yield
    await close_postgres_checkpoint_saver()
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
        {
            "name": "Human Approval",
            "description": "Resume interrupted agent runs and inspect run state.",
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
    @app.middleware("http")
    async def request_timing_middleware(
        request: Request, call_next
    ) -> Response:  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        set_request_id(request_id)
        started = perf_counter()
        response = await call_next(request)
        elapsed_ms = (perf_counter() - started) * 1000
        response.headers["x-request-id"] = request_id
        response.headers["x-process-time-ms"] = f"{elapsed_ms:.1f}"
        logger.info(
            "api.request method=%s path=%s status=%s request_id=%s elapsed_ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
            elapsed_ms,
        )
        return response

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
    app.include_router(human_approval_router.router, prefix=api_prefix)

    return app


app = create_app()
