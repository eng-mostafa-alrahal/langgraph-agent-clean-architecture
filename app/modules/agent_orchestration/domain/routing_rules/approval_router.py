"""Deterministic routing logic for human-in-the-loop approval gates.

Pure functions — no LLM calls, no I/O.  They inspect state and return
the name of the next node the graph should traverse.
"""

from __future__ import annotations

from typing import Literal

from app.modules.agent_orchestration.domain.states.supervisor_state import SupervisorState


def route_to_human_review(
    state: SupervisorState,
) -> Literal["human_review", "chat", "end"]:
    """After delegation: errors → END, researcher → human_review, chat → direct."""
    if state.get("error"):
        return "end"
    next_agent = state.get("next_agent") or "chat"
    if next_agent == "researcher":
        return "human_review"
    return next_agent  # type: ignore[return-value]


def route_after_human_review(
    state: SupervisorState,
) -> Literal["researcher", "chat", "end"]:
    """After human review: approved → originally intended agent, otherwise → END."""
    if state.get("human_feedback") == "approved":
        return state.get("next_agent") or "chat"  # type: ignore[return-value]
    return "end"
