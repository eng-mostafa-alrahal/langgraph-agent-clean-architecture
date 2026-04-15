"""State schema for the researcher sub-graph."""

from __future__ import annotations

import operator
from typing import Annotated

from app.modules.agent_orchestration.domain.states.base_state import BaseAgentState


class ResearcherState(BaseAgentState):
    search_queries: list[str]
    retrieved_context: Annotated[list[str], operator.add]
    context_is_sufficient: bool
