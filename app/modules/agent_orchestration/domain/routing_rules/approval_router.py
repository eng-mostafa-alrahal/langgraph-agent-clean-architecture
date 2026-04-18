"""Deterministic routing logic for human-in-the-loop approval gates.

Pure functions — no LLM calls, no I/O.  They inspect state and return
the name of the next node the graph should traverse.
"""

from __future__ import annotations

from typing import Literal

from app.modules.agent_orchestration.domain.states.supervisor_state import SupervisorState


def _normalize_agent(name: str | None) -> str:
    """Map legacy routing value ``file_writer`` → ``workspace``."""
    if not name:
        return "chat"
    if name == "file_writer":
        return "workspace"
    return name


def route_to_human_review(
    state: SupervisorState,
) -> Literal["human_review", "researcher", "chat", "end"]:
    """After delegation: errors → END; workspace → human_review; researcher/chat → direct."""
    if state.get("error"):
        return "end"
    next_agent = _normalize_agent(state.get("next_agent"))
    if next_agent == "workspace":
        return "human_review"
    if next_agent == "researcher":
        return "researcher"
    return next_agent  # type: ignore[return-value]


def route_after_human_review(
    state: SupervisorState,
) -> Literal["researcher", "chat", "workspace", "end"]:
    """After human review: approved → originally intended agent, otherwise → END."""
    if state.get("human_feedback") == "approved":
        return _normalize_agent(state.get("next_agent"))  # type: ignore[return-value]
    return "end"
