"""Shared chat node — usable in any sub-graph that needs a basic LLM reply."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from app.modules.agent_orchestration.domain.states.base_state import BaseAgentState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.config.prompt_factory import (
    build_chat_prompt,
)


def make_chat_node(llm: BaseChatModel):
    prompt = build_chat_prompt()
    chain = prompt | llm

    async def chat_node(state: BaseAgentState) -> dict:
        response = await chain.ainvoke({"messages": state["messages"]})
        if isinstance(response, AIMessage):
            return {"messages": [response]}
        return {"messages": [AIMessage(content=str(response))]}

    return chat_node
