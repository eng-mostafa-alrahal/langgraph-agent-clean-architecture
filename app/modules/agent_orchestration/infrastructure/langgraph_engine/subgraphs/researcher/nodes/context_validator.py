"""Node that validates whether retrieved context is sufficient."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.infrastructure.llm_gateways.structured_output import with_pydantic_output
from app.modules.agent_orchestration.domain.schemas.research_decision import ResearchDecision
from app.modules.agent_orchestration.domain.states.researcher_state import ResearcherState


def make_context_validator_node(llm: BaseChatModel):
    structured_llm = with_pydantic_output(llm, ResearchDecision)

    async def context_validator(state: ResearcherState) -> dict:
        context = state.get("retrieved_context", [])
        if not context:
            return {
                "context_is_sufficient": False,
                "search_queries": ["general information about the topic"],
            }

        prompt = (
            f"Given this context:\n\n{chr(10).join(context)}\n\n"
            "Decide whether the context is sufficient to answer the user's question. "
            "If not, provide follow-up search queries.\n"
            "Reply with a single json object only (no XML or markdown)."
        )
        # Groq requires the word "json" in messages when using response_format json_object.
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
