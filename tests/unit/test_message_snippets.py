"""Tests for recent human-message grounding."""

from langchain_core.messages import AIMessage, HumanMessage

from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.message_snippets import (
    recent_human_turns_as_text,
)


def test_recent_human_turns_joins_last_messages():
    msgs = [
        HumanMessage(content="first"),
        AIMessage(content="ok"),
        HumanMessage(content="second ask"),
    ]
    assert recent_human_turns_as_text(msgs, max_turns=3) == "first\n---\nsecond ask"


def test_recent_human_turns_respects_max_turns():
    msgs = [HumanMessage(content=str(i)) for i in range(5)]
    out = recent_human_turns_as_text(msgs, max_turns=2)
    assert out == "3\n---\n4"
