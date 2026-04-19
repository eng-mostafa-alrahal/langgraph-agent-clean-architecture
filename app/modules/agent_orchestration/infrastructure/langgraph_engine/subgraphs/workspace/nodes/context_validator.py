"""Validate whether extended-tool results satisfy the user's goal."""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.infrastructure.llm_gateways.structured_output import with_pydantic_output
from app.modules.agent_orchestration.application.ports.prompt_provider_port import IPromptProvider
from app.modules.agent_orchestration.domain.prompts.context import PromptContext
from app.modules.agent_orchestration.domain.prompts.intent import PromptIntent
from app.modules.agent_orchestration.domain.prompts.schema_compact import compact_schema_for_llm
from app.modules.agent_orchestration.domain.schemas.research_decision import WorkspaceLoopDecision
from app.modules.agent_orchestration.domain.states.researcher_state import ResearcherState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.prompt_trace_config import (
    trace_config_for_structured_pair,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.message_snippets import (  # noqa: E501
    recent_human_turns_as_text,
)

logger = logging.getLogger(__name__)


def make_workspace_context_validator_node(llm: BaseChatModel, *, prompt_provider: IPromptProvider):
    structured_llm = with_pydantic_output(llm, WorkspaceLoopDecision)

    async def context_validator(state: ResearcherState) -> dict:
        context = state.get("retrieved_context", [])
        user_block = recent_human_turns_as_text(state.get("messages", []))
        if not context:
            return {
                "context_is_sufficient": False,
                "search_queries": ["Run the tools needed to address the user's request"],
            }

        goal_section = f"User request (recent turns):\n{user_block}\n\n" if user_block else ""

        system_rendered = prompt_provider.resolve_prompt(
            PromptIntent.STRUCTURED_OUTPUT_SYSTEM,
            PromptContext(),
        )
        human_rendered = prompt_provider.resolve_prompt(
            PromptIntent.WORKSPACE_CONTEXT_VALIDATION,
            PromptContext(
                goal_section=goal_section,
                retrieved_evidence=chr(10).join(context),
                compact_schema=compact_schema_for_llm(WorkspaceLoopDecision),
            ),
        )

        trace_cfg = trace_config_for_structured_pair(
            system_rendered.metadata,
            human_rendered.metadata,
        )

        logger.info(
            "workspace_context_validation_prompt system=%s human=%s",
            system_rendered.metadata.get("asset_path"),
            human_rendered.metadata.get("asset_path"),
        )

        decision: WorkspaceLoopDecision = await structured_llm.ainvoke(
            [
                SystemMessage(content=system_rendered.content),
                HumanMessage(content=human_rendered.content),
            ],
            config=trace_cfg,
        )  # type: ignore[assignment]
        hints = decision.follow_up_hints or []
        return {
            "context_is_sufficient": not decision.needs_more_tool_calls,
            "search_queries": hints,
        }

    return context_validator
