"""Human-review gate node — pauses the graph until a human resumes it.

Uses LangGraph's ``interrupt()`` primitive.  When the graph reaches this
node it persists its checkpoint and returns control to the caller.  The
caller later resumes via ``Command(resume=<payload>)`` and the
``interrupt()`` call returns that payload.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langgraph.types import interrupt


def human_review_node(state: dict[str, Any]) -> dict[str, Any]:
    decision: dict[str, Any] = interrupt(
        {
            "message": "Human approval required before executing this task.",
            "next_agent": state.get("next_agent"),
            "reasoning": state.get("delegation_reasoning"),
        }
    )

    action: str = (
        decision.get("action", "rejected") if isinstance(decision, dict) else str(decision)
    )
    feedback: str | None = decision.get("feedback") if isinstance(decision, dict) else None

    updates: dict[str, Any] = {"human_feedback": action}

    if action != "approved":
        msg = "The requested action was not approved."
        if feedback:
            msg += f" User feedback: {feedback}"
        updates["messages"] = [AIMessage(content=msg)]

    return updates
