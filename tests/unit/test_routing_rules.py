"""Verify pure-function routing logic."""

from app.modules.agent_orchestration.domain.routing_rules.approval_router import (
    route_after_human_review,
    route_to_human_review,
)
from app.modules.agent_orchestration.domain.routing_rules.local_time_intent import (
    looks_like_local_time_question,
)
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


def test_approval_routes_workspace_to_human_review():
    state = {"error": None, "next_agent": "workspace"}
    assert route_to_human_review(state) == "human_review"  # type: ignore[arg-type]


def test_approval_routes_researcher_directly_without_human_review():
    state = {"error": None, "next_agent": "researcher"}
    assert route_to_human_review(state) == "researcher"  # type: ignore[arg-type]


def test_approval_normalizes_legacy_file_writer_to_workspace():
    state = {"error": None, "next_agent": "file_writer"}
    assert route_to_human_review(state) == "human_review"  # type: ignore[arg-type]


def test_approval_after_human_review_returns_workspace_when_approved():
    state = {"human_feedback": "approved", "next_agent": "workspace"}
    assert route_after_human_review(state) == "workspace"  # type: ignore[arg-type]


def test_approval_after_human_review_normalizes_legacy_file_writer():
    state = {"human_feedback": "approved", "next_agent": "file_writer"}
    assert route_after_human_review(state) == "workspace"  # type: ignore[arg-type]


def test_local_time_intent_matches_common_phrases():
    assert looks_like_local_time_question("what is the current time in Tokyo")
    assert looks_like_local_time_question("What's the time in London?")
    assert looks_like_local_time_question("current time in Paris")
    assert looks_like_local_time_question("local time in Austin, TX")


def test_local_time_intent_avoids_false_positives():
    assert not looks_like_local_time_question("closing time in Tokyo")
    assert not looks_like_local_time_question("tell me about Tokyo")
