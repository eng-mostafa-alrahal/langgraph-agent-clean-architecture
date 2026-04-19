"""Use-case: execute the agent graph for a single user message."""

from __future__ import annotations

from app.core.exceptions import AgentExecutionError, AppException, RateLimitExceededError
from app.modules.agent_orchestration.application.agent_error_detail import (
    format_agent_execution_detail,
)
from app.modules.agent_orchestration.application.dtos.agent_result import AgentRunResult
from app.modules.agent_orchestration.application.ports.agent_orchestrator_port import (
    IAgentOrchestrator,
)


class ExecuteGraphUseCase:
    def __init__(self, orchestrator: IAgentOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def execute(
        self,
        user_message: str,
        *,
        session_id: str,
        user_id: str,
    ) -> AgentRunResult:
        try:
            return await self._orchestrator.invoke(
                user_message, session_id=session_id, user_id=user_id
            )
        except AppException:
            raise
        except Exception as exc:
            detail = str(exc)
            normalized = detail.lower()
            if any(
                token in normalized
                for token in (
                    "resource_exhausted",
                    "quota exceeded",
                    "rate limit",
                    "too many requests",
                    "429",
                )
            ):
                raise RateLimitExceededError(
                    detail=(
                        "LLM provider quota or rate limit exceeded. "
                        "Please retry later or update provider limits."
                    )
                ) from exc
            raise AgentExecutionError(detail=format_agent_execution_detail(exc)) from exc
