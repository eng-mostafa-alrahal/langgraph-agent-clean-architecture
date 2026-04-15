"""Contract for the top-level agent orchestrator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any


class IAgentOrchestrator(ABC):
    @abstractmethod
    async def invoke(
        self,
        user_message: str,
        *,
        session_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Run the full graph synchronously and return the final state."""
        ...

    @abstractmethod
    async def stream(
        self,
        user_message: str,
        *,
        session_id: str,
        user_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield incremental state updates as the graph executes."""
        ...
