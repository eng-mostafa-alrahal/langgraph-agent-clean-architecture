"""Deterministic conditional-edge logic for the supervisor graph.

Pure functions — no LLM calls, no I/O.  They inspect state and return
the name of the next node the graph should traverse.
"""

from __future__ import annotations

from typing import Literal

from app.modules.agent_orchestration.domain.states.supervisor_state import SupervisorState


def route_supervisor(
    state: SupervisorState,
) -> Literal["researcher", "chat", "workspace", "end"]:
    if state.get("error"):
        return "end"
    return state.get("next_agent") or "chat"
