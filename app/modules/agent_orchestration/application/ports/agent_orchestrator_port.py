"""Contract for the top-level agent orchestrator.

The port exposes only framework-agnostic DTOs. Implementations are free to
use LangGraph / LangChain / anything else internally, but must translate
those types to :mod:`agent_orchestration.application.dtos` at the boundary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.agent_orchestration.application.dtos.agent_result import (
    AgentEvent,
    AgentRunResult,
    AgentStateSnapshot,
)


class IAgentOrchestrator(ABC):
    @abstractmethod
    async def invoke(
        self,
        user_message: str,
        *,
        session_id: str,
        user_id: str,
    ) -> AgentRunResult:
        """Run the full graph synchronously and return the final result."""
        ...

    @abstractmethod
    def stream(
        self,
        user_message: str,
        *,
        session_id: str,
        user_id: str,
    ) -> AsyncIterator[AgentEvent]:
        """Yield incremental events as the graph executes."""
        ...

    @abstractmethod
    async def resume(
        self,
        *,
        thread_id: str,
        action: str,
        feedback: str | None = None,
    ) -> AgentRunResult:
        """Resume an interrupted graph run with human feedback."""
        ...

    @abstractmethod
    async def get_state(self, *, thread_id: str) -> AgentStateSnapshot:
        """Return the current state snapshot of a graph run."""
        ...
