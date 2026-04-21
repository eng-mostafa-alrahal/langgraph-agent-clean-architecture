"""FastAPI Depends() factories — wires use-cases to HTTP handlers."""

from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from app.core.config.di_container import get_container
from app.core.config.settings import Settings, get_settings
from app.core.exceptions import MCPBootstrapError
from app.core.security.jwt_service import verify_access_token
from app.infrastructure.database.postgres.unit_of_work import SqlAlchemyUnitOfWork
from app.modules.agent_orchestration.application.ports.agent_orchestrator_port import (
    IAgentOrchestrator,
)
from app.modules.agent_orchestration.application.use_cases.execute_graph_uc import (
    ExecuteGraphUseCase,
)
from app.modules.agent_orchestration.application.use_cases.resume_graph_uc import (
    ResumeGraphUseCase,
)
from app.modules.agent_orchestration.application.use_cases.stream_graph_events_uc import (
    StreamGraphEventsUseCase,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.main_graph_builder import (
    MainGraphOrchestrator,
)
from app.modules.agent_orchestration.infrastructure.registries.llm_registry import LLMRegistry
from app.modules.agent_orchestration.infrastructure.registries.tool_registry import ToolRegistry
from app.modules.sessions.use_cases.session_service import SessionService
from app.modules.users.use_cases.user_service import UserService


# ── Auth dependency ──────────────────────────────────────────────
async def get_current_user_id(
    authorization: Annotated[str, Header()],
) -> UUID:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        from app.core.exceptions import AuthenticationError

        raise AuthenticationError("Missing or malformed Authorization header.")
    return verify_access_token(token)


# ── UoW ──────────────────────────────────────────────────────────
def get_uow() -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork()


# ── Services ─────────────────────────────────────────────────────
def get_user_service(uow: SqlAlchemyUnitOfWork = Depends(get_uow)) -> UserService:
    return UserService(uow)


def get_session_service(uow: SqlAlchemyUnitOfWork = Depends(get_uow)) -> SessionService:
    return SessionService(uow)


# ── Agent use-cases ──────────────────────────────────────────────
def _build_tool_registry() -> ToolRegistry:
    import logging

    from app.modules.agent_orchestration.infrastructure.tools.knowledge_retriever.search_toolset import (  # noqa: E501
        RAGSearchTool,
        WebSearchTool,
    )
    from app.modules.agent_orchestration.infrastructure.tools.local_time_tool import (
        GetLocalTimeTool,
    )

    log = logging.getLogger(__name__)
    settings = get_settings()
    registry = ToolRegistry()

    if settings.TAVILY_API_KEY:
        registry.register(WebSearchTool(api_key=settings.TAVILY_API_KEY))
    else:
        log.info(
            "TAVILY_API_KEY is not set — web_search is disabled. "
            "Add it to .env for live sports, news, and up-to-date answers."
        )

    retriever = None
    if settings.PGVECTOR_ENABLED and settings.OPENAI_API_KEY:
        try:
            from app.infrastructure.database.postgres.vector_store import (
                build_pgvector_retriever,
            )

            retriever = build_pgvector_retriever()
        except Exception as exc:
            log.warning(
                "PGVector store unavailable — RAG tool will run without a retriever: %s",
                exc,
            )
            if settings.DEBUG:
                log.exception("PGVector initialisation failed")

    registry.register(RAGSearchTool(retriever=retriever))
    registry.register(
        GetLocalTimeTool(user_agent=f"{settings.APP_NAME}/{settings.APP_VERSION}"),
    )

    try:
        mcp_tools = get_container().resolve("mcp_tools")  # type: ignore[assignment]
    except LookupError:
        mcp_tools = []

    for tool in mcp_tools:
        if tool.name in registry.list_available():
            raise MCPBootstrapError(
                detail=(
                    f"MCP tool '{tool.name}' collides with a built-in tool name. "
                    "Rename the MCP server key or adjust external tool names."
                ),
            )
        registry.register(tool)

    return registry


def _orchestrator_tool_config_sig(settings: Settings) -> tuple[object, ...]:
    """When this tuple changes, the compiled graph must be rebuilt (tools differ)."""
    mcp_sig = json.dumps(
        [spec.model_dump(mode="json") for spec in settings.MCP_SERVERS],
        sort_keys=True,
    )
    return (
        settings.TAVILY_API_KEY,
        settings.PGVECTOR_ENABLED,
        bool(settings.OPENAI_API_KEY),
        settings.DEFAULT_LLM_PROVIDER,
        settings.DEFAULT_MODEL_NAME,
        settings.AGENT_MAX_CONTEXT_TOKENS,
        settings.SUPERVISOR_ROUTING_MAX_TOKENS,
        settings.MAX_TOOL_OUTPUT_CHARS,
        settings.MEMORY_SUMMARIZATION_TRIGGER_MESSAGES,
        settings.MEMORY_SUMMARIZATION_KEEP_RECENT_MESSAGES,
        settings.MEMORY_SUMMARY_MAX_CHARS,
        settings.MEMORY_SUMMARIZER_PROVIDER,
        settings.MEMORY_SUMMARIZER_MODEL_NAME,
        mcp_sig,
    )


def _get_orchestrator() -> MainGraphOrchestrator:
    """Build once per compatible tool config; rebuild if Tavily / PGVector / OpenAI flags change."""
    container = get_container()
    settings = get_settings()
    sig = _orchestrator_tool_config_sig(settings)
    try:
        existing = container.resolve("orchestrator")
        if getattr(existing, "_tool_config_sig", None) == sig:
            return existing  # type: ignore[return-value]
    except LookupError:
        pass

    llm_registry = LLMRegistry()
    tool_registry = _build_tool_registry()
    orchestrator = MainGraphOrchestrator(llm_registry, tool_registry)
    orchestrator._tool_config_sig = sig  # type: ignore[attr-defined]
    container.register_singleton("orchestrator", orchestrator)
    return orchestrator


def get_execute_graph_uc() -> ExecuteGraphUseCase:
    return ExecuteGraphUseCase(_get_orchestrator())


def get_stream_graph_events_uc() -> StreamGraphEventsUseCase:
    return StreamGraphEventsUseCase(_get_orchestrator())


def get_resume_graph_uc() -> ResumeGraphUseCase:
    return ResumeGraphUseCase(_get_orchestrator())


def get_run_state_uc() -> IAgentOrchestrator:
    """Return the orchestrator (as its port) for state-inspection endpoints."""
    return _get_orchestrator()
