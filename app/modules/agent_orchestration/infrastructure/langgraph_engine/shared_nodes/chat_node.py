"""Shared chat node — usable in any sub-graph that needs a basic LLM reply."""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from app.modules.agent_orchestration.application.ports.prompt_provider_port import IPromptProvider
from app.modules.agent_orchestration.domain.prompts.context import PromptContext
from app.modules.agent_orchestration.domain.prompts.intent import PromptIntent
from app.modules.agent_orchestration.domain.states.base_state import BaseAgentState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.mappers.prompt_mapper import (
    to_chat_prompt_template,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.prompt_trace_config import (
    trace_run_config_from_metadata,
)

logger = logging.getLogger(__name__)


def make_chat_node(llm: BaseChatModel, *, prompt_provider: IPromptProvider):
    rendered = prompt_provider.resolve_prompt(PromptIntent.CHAT_AGENT, PromptContext())
    prompt = to_chat_prompt_template(rendered)
    trace_cfg = trace_run_config_from_metadata(rendered.metadata)
    logger.info(
        "chat_prompt_loaded intent=%s version=%s asset=%s",
        rendered.metadata.get("intent"),
        rendered.metadata.get("version"),
        rendered.metadata.get("asset_path"),
    )
    chain = prompt | llm

    async def chat_node(state: BaseAgentState) -> dict:
        response = await chain.ainvoke({"messages": state["messages"]}, config=trace_cfg)
        if isinstance(response, AIMessage):
            return {"messages": [response]}
        return {"messages": [AIMessage(content=str(response))]}

    return chat_node
