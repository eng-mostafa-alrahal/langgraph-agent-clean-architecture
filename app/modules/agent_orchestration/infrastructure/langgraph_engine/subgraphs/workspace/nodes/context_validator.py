"""Validate whether extended-tool results satisfy the user's goal."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.infrastructure.llm_gateways.structured_output import with_pydantic_output
from app.modules.agent_orchestration.domain.schemas.research_decision import WorkspaceLoopDecision
from app.modules.agent_orchestration.domain.states.researcher_state import ResearcherState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.message_snippets import (
    recent_human_turns_as_text,
)


def make_workspace_context_validator_node(llm: BaseChatModel):
    structured_llm = with_pydantic_output(llm, WorkspaceLoopDecision)

    async def context_validator(state: ResearcherState) -> dict:
        context = state.get("retrieved_context", [])
        user_block = recent_human_turns_as_text(state.get("messages", []))
        if not context:
            return {
                "context_is_sufficient": False,
                "search_queries": ["Run the tools needed to address the user's request"],
            }

        goal_section = (
            f"User request (recent turns):\n{user_block}\n\n"
            if user_block
            else ""
        )
        prompt = (
            f"{goal_section}"
            f"Latest tool output from this subgraph:\n\n{chr(10).join(context)}\n\n"
            "Decide if the user's goal is fully satisfied by what these tools produced, "
            "or if another round of tool calls is needed.\n"
            "Set needs_more_tool_calls=true only when more tool execution is clearly required "
            "(missing read, failed write, need to list before delete, verify a result, etc.).\n"
            "If the user only wanted research/chat, or the task is done or blocked with a clear "
            "message, set needs_more_tool_calls=false.\n"
            "When more tools are needed, put short follow_up_hints (not full tool XML) — "
            "each hint guides the next planning step.\n"
            "Reply with a single json object only (no XML or markdown)."
        )
        decision: WorkspaceLoopDecision = await structured_llm.ainvoke(
            [
                SystemMessage(content="You output structured answers as json."),
                HumanMessage(content=prompt),
            ]
        )  # type: ignore[assignment]
        hints = decision.follow_up_hints or []
        return {
            "context_is_sufficient": not decision.needs_more_tool_calls,
            "search_queries": hints,
        }

    return context_validator
