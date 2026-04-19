"""Node that uses the LLM to decide which sub-agent should handle the request."""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from app.infrastructure.llm_gateways.structured_output import with_pydantic_output
from app.modules.agent_orchestration.application.ports.prompt_provider_port import IPromptProvider
from app.modules.agent_orchestration.domain.prompts.context import PromptContext
from app.modules.agent_orchestration.domain.prompts.intent import PromptIntent
from app.modules.agent_orchestration.domain.prompts.schema_compact import compact_schema_for_llm
from app.modules.agent_orchestration.domain.routing_rules.local_time_intent import (
    looks_like_local_time_question,
)
from app.modules.agent_orchestration.domain.schemas.research_decision import DelegationDecision
from app.modules.agent_orchestration.domain.states.supervisor_state import SupervisorState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.mappers.prompt_mapper import (
    to_chat_prompt_template,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.prompt_trace_config import (
    trace_run_config_from_metadata,
)

logger = logging.getLogger(__name__)

_LEGACY_NEXT_AGENT = {"file_writer": "workspace"}


def _last_human_plain_text(messages: list[BaseMessage]) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage) or getattr(m, "type", None) == "human":
            c = m.content
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                parts: list[str] = []
                for block in c:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(str(block.get("text", "")))
                return " ".join(parts).strip()
            return str(c)
    return ""


def make_task_delegator_node(
    llm: BaseChatModel,
    *,
    prompt_provider: IPromptProvider,
    include_workspace_agent: bool = True,
):
    structured_llm = with_pydantic_output(llm, DelegationDecision)

    async def task_delegator(state: SupervisorState) -> dict:
        compact_schema = compact_schema_for_llm(DelegationDecision)
        prompt_ctx = PromptContext(
            compact_schema=compact_schema,
            include_workspace_agent=include_workspace_agent,
        )
        rendered = prompt_provider.resolve_prompt(PromptIntent.SUPERVISOR_ROUTING, prompt_ctx)

        logger.info(
            "supervisor_prompt_rendered intent=%s version=%s asset=%s",
            rendered.metadata.get("intent"),
            rendered.metadata.get("version"),
            rendered.metadata.get("asset_path"),
        )

        prompt = to_chat_prompt_template(rendered)
        chain = prompt | structured_llm
        trace_cfg = trace_run_config_from_metadata(rendered.metadata)

        decision: DelegationDecision = await chain.ainvoke(  # type: ignore[assignment]
            {"messages": state["messages"]},
            config=trace_cfg,
        )
        raw = decision.next_agent.strip().lower().replace("-", "_")
        raw = _LEGACY_NEXT_AGENT.get(raw, raw)
        allowed = {"researcher", "chat", "end"}
        if include_workspace_agent:
            allowed.add("workspace")
        next_agent = raw if raw in allowed else "chat"
        reasoning = decision.reasoning
        user_text = _last_human_plain_text(state["messages"])
        if looks_like_local_time_question(user_text) and next_agent == "chat":
            next_agent = "researcher"
            reasoning = (
                f"{reasoning} (Routing override: local time in a place requires get_local_time.)"
            )
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
