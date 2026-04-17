"""Use-case: resume an interrupted graph run with human feedback."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import AgentExecutionError, AppException, RateLimitExceededError
from app.modules.agent_orchestration.application.agent_error_detail import (
    format_agent_execution_detail,
)
from app.modules.agent_orchestration.application.ports.agent_orchestrator_port import (
    IAgentOrchestrator,
)


class ResumeGraphUseCase:
    def __init__(self, orchestrator: IAgentOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def execute(
        self,
        *,
        thread_id: str,
        action: str,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        try:
            return await self._orchestrator.resume(
                thread_id=thread_id,
                action=action,
                feedback=feedback,
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
                    detail="LLM provider quota or rate limit exceeded. Please retry later or update provider limits."
                ) from exc
            raise AgentExecutionError(detail=format_agent_execution_detail(exc)) from exc
