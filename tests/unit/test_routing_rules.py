"""Verify pure-function routing logic."""

from app.modules.agent_orchestration.domain.routing_rules.researcher_router import (
    route_researcher,
)
from app.modules.agent_orchestration.domain.routing_rules.supervisor_router import (
    route_supervisor,
)


def test_supervisor_routes_to_end_on_error():
    state = {"error": "something broke", "next_agent": "researcher"}
    assert route_supervisor(state) == "end"  # type: ignore[arg-type]


def test_supervisor_routes_to_next_agent():
    state = {"error": None, "next_agent": "researcher"}
    assert route_supervisor(state) == "researcher"  # type: ignore[arg-type]


def test_supervisor_defaults_to_chat():
    state = {"error": None, "next_agent": None}
    assert route_supervisor(state) == "chat"  # type: ignore[arg-type]


def test_researcher_routes_to_search():
    state = {"error": None, "context_is_sufficient": False, "search_queries": ["query1"]}
    assert route_researcher(state) == "search"  # type: ignore[arg-type]


def test_researcher_routes_to_synthesize():
    state = {"error": None, "context_is_sufficient": True, "search_queries": []}
    assert route_researcher(state) == "synthesize"  # type: ignore[arg-type]


def test_researcher_routes_to_end_on_error():
    state = {"error": "fail", "context_is_sufficient": False, "search_queries": []}
    assert route_researcher(state) == "end"  # type: ignore[arg-type]
