"""Node that uses the LLM to decide which sub-agent should handle the request."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.infrastructure.llm_gateways.structured_output import with_pydantic_output
from app.modules.agent_orchestration.domain.schemas.research_decision import DelegationDecision
from app.modules.agent_orchestration.domain.states.supervisor_state import SupervisorState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.config.prompt_factory import (
    build_supervisor_prompt,
)


def make_task_delegator_node(llm: BaseChatModel):
    prompt = build_supervisor_prompt()
    structured_llm = with_pydantic_output(llm, DelegationDecision)

    async def task_delegator(state: SupervisorState) -> dict:
        chain = prompt | structured_llm
        decision: DelegationDecision = await chain.ainvoke({"messages": state["messages"]})  # type: ignore[assignment]
        return {
            "next_agent": decision.next_agent,
            "delegation_reasoning": decision.reasoning,
        }

    return task_delegator
