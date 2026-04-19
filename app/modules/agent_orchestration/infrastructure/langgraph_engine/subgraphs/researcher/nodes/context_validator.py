"""Node that validates whether retrieved context is sufficient."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.infrastructure.llm_gateways.structured_output import with_pydantic_output
from app.modules.agent_orchestration.domain.schemas.research_decision import ResearchDecision
from app.modules.agent_orchestration.domain.states.researcher_state import ResearcherState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.message_snippets import (  # noqa: E501
    recent_human_turns_as_text,
)


def make_context_validator_node(llm: BaseChatModel):
    structured_llm = with_pydantic_output(llm, ResearchDecision)

    async def context_validator(state: ResearcherState) -> dict:
        context = state.get("retrieved_context", [])
        user_block = recent_human_turns_as_text(state.get("messages", []))
        if not context:
            return {
                "context_is_sufficient": False,
                "search_queries": ["general information about the topic"],
            }

        goal_section = f"User request (recent turns):\n{user_block}\n\n" if user_block else ""
        prompt = (
            f"{goal_section}"
            f"Retrieved evidence from tools this subgraph:\n\n{chr(10).join(context)}\n\n"
            "Decide whether this evidence is sufficient to answer what the user asked "
            "(use the user request above).\n"
            "If more external or internal retrieval is clearly needed, set "
            "needs_more_research=true and provide concise follow-up search_queries.\n"
            "If there is enough to answer — or the user's question cannot be answered by "
            "search at all — set needs_more_research=false.\n"
            "Reply with a single json object only (no XML or markdown)."
        )
        decision: ResearchDecision = await structured_llm.ainvoke(
            [
                SystemMessage(content="You output structured answers as json."),
                HumanMessage(content=prompt),
            ]
        )  # type: ignore[assignment]
        return {
            "context_is_sufficient": not decision.needs_more_research,
            "search_queries": decision.search_queries,
        }

    return context_validator
