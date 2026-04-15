"""Compiles all sub-graphs into the master agent graph.

This is the single entry-point the application layer calls via the
IAgentOrchestrator port.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.core.config.settings import get_settings
from app.core.exceptions import GraphCompilationError
from app.modules.agent_orchestration.application.ports.agent_orchestrator_port import (
    IAgentOrchestrator,
)
from app.modules.agent_orchestration.application.ports.llm_registry_port import ILLMRegistry
from app.modules.agent_orchestration.application.ports.tool_registry_port import IToolRegistry
from app.modules.agent_orchestration.domain.states.supervisor_state import SupervisorState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.error_handler_node import (
    error_handler_node,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.subgraphs.supervisor.supervisor_graph import (
    build_supervisor_graph,
)

logger = logging.getLogger(__name__)


class MainGraphOrchestrator(IAgentOrchestrator):
    def __init__(
        self,
        llm_registry: ILLMRegistry,
        tool_registry: IToolRegistry,
    ) -> None:
        self._llm_registry = llm_registry
        self._tool_registry = tool_registry
        self._compiled: CompiledStateGraph | None = None

    def _compile(self) -> CompiledStateGraph:
        if self._compiled is not None:
            return self._compiled

        try:
            settings = get_settings()
            llm = self._llm_registry.get_model(
                settings.DEFAULT_LLM_PROVIDER,
                settings.DEFAULT_MODEL_NAME,
            )
            researcher_llm = llm
            if (
                settings.DEFAULT_LLM_PROVIDER == "groq"
                and settings.GROQ_TOOL_CALLING_MODEL
                and settings.GROQ_TOOL_CALLING_MODEL != settings.DEFAULT_MODEL_NAME
            ):
                researcher_llm = self._llm_registry.get_model(
                    "groq",
                    settings.GROQ_TOOL_CALLING_MODEL,
                )
            all_tools = self._tool_registry.get_tools(self._tool_registry.list_available())

            supervisor_subgraph = build_supervisor_graph(
                llm,
                all_tools,
                researcher_llm=researcher_llm,
            ).compile()

            master = StateGraph(SupervisorState)
            master.add_node("supervisor", supervisor_subgraph)
            master.add_node("error_handler", error_handler_node)

            master.set_entry_point("supervisor")
            master.add_edge("supervisor", "error_handler")
            master.add_edge("error_handler", END)

            self._compiled = master.compile()
            logger.info("Master agent graph compiled successfully")
            return self._compiled
        except Exception as exc:
            raise GraphCompilationError(detail=str(exc)) from exc

    # ── IAgentOrchestrator implementation ────────────────────────
    async def invoke(
        self,
        user_message: str,
        *,
        session_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        graph = self._compile()
        initial_state: dict[str, Any] = {
            "messages": [HumanMessage(content=user_message)],
            "session_id": session_id,
            "user_id": user_id,
            "error": None,
            "next_agent": None,
            "delegation_reasoning": None,
        }
        config = {"configurable": {"thread_id": session_id}}
        return await graph.ainvoke(initial_state, config=config)

    async def stream(
        self,
        user_message: str,
        *,
        session_id: str,
        user_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        graph = self._compile()
        initial_state: dict[str, Any] = {
            "messages": [HumanMessage(content=user_message)],
            "session_id": session_id,
            "user_id": user_id,
            "error": None,
            "next_agent": None,
            "delegation_reasoning": None,
        }
        config = {"configurable": {"thread_id": session_id}}
        async for event in graph.astream(initial_state, config=config):
            yield event
