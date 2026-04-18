"""Node that uses the LLM to decide which sub-agent should handle the request."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.infrastructure.llm_gateways.structured_output import with_pydantic_output
from app.modules.agent_orchestration.domain.schemas.research_decision import DelegationDecision
from app.modules.agent_orchestration.domain.states.supervisor_state import SupervisorState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.config.prompt_factory import (
    build_supervisor_prompt,
)

_LEGACY_NEXT_AGENT = {"file_writer": "workspace"}


def make_task_delegator_node(llm: BaseChatModel, *, include_workspace_agent: bool = True):
    prompt = build_supervisor_prompt(include_workspace_agent=include_workspace_agent)
    structured_llm = with_pydantic_output(llm, DelegationDecision)

    async def task_delegator(state: SupervisorState) -> dict:
        chain = prompt | structured_llm
        decision: DelegationDecision = await chain.ainvoke({"messages": state["messages"]})  # type: ignore[assignment]
        raw = decision.next_agent.strip().lower().replace("-", "_")
        raw = _LEGACY_NEXT_AGENT.get(raw, raw)
        allowed = {"researcher", "chat", "end"}
        if include_workspace_agent:
            allowed.add("workspace")
        next_agent = raw if raw in allowed else "chat"
        reasoning = decision.reasoning
        if raw == "workspace" and not include_workspace_agent:
            next_agent = "chat"
            reasoning = (
                f"{reasoning} (Routing note: no extended workspace tools are registered — "
                "using chat instead of workspace.)"
            )
        return {
            "next_agent": next_agent,
            "delegation_reasoning": reasoning,
        }

    return task_delegator
