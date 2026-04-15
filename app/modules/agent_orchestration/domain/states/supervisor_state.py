"""State schema for the supervisor sub-graph."""

from __future__ import annotations

from typing import Literal

from app.modules.agent_orchestration.domain.states.base_state import BaseAgentState


class SupervisorState(BaseAgentState):
    next_agent: Literal["researcher", "chat", "end"] | None
    delegation_reasoning: str | None
