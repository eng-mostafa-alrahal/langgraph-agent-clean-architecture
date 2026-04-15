"""Deterministic conditional-edge logic for the researcher graph."""

from __future__ import annotations

from typing import Literal

from app.modules.agent_orchestration.domain.states.researcher_state import ResearcherState


def route_researcher(state: ResearcherState) -> Literal["search", "synthesize", "end"]:
    if state.get("error"):
        return "end"
    if state.get("context_is_sufficient"):
        return "synthesize"
    if len(state.get("search_queries", [])) > 0:
        return "search"
    return "end"
