"""Compiles all sub-graphs into the master agent graph.

This module is the single LangGraph adapter that fulfils
:class:`IAgentOrchestrator`.  It is the *only* place in the codebase where
LangGraph / LangChain types are allowed; its public surface returns pure
DTOs from ``agent_orchestration.application.dtos``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from app.core.config.settings import get_settings
from app.core.exceptions import GraphCompilationError, GraphNotInterruptedError
from app.core.observability.request_context import get_request_id
from app.modules.agent_orchestration.application.dtos.agent_result import (
    AgentEvent,
    AgentRunResult,
    AgentStateSnapshot,
)
from app.modules.agent_orchestration.application.ports.agent_orchestrator_port import (
    IAgentOrchestrator,
)
from app.modules.agent_orchestration.application.ports.llm_registry_port import ILLMRegistry
from app.modules.agent_orchestration.application.ports.tool_registry_port import IToolRegistry
from app.modules.agent_orchestration.domain.states.supervisor_state import SupervisorState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.mappers.state_mapper import (
    snapshot_is_paused,
    to_agent_events,
    to_run_result,
    to_state_snapshot,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.memory.postgres_saver import (
    ensure_checkpointer_ready,
    get_postgres_saver,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.error_handler_node import (  # noqa: E501
    error_handler_node,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.subgraphs.supervisor.supervisor_graph import (  # noqa: E501
    build_supervisor_graph,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.tool_partition import (
    partition_tools_for_agents,
)
from app.modules.agent_orchestration.infrastructure.registries.file_prompt_registry import (
    FilePromptRegistry,
)

logger = logging.getLogger(__name__)
SLOW_STEP_MS = 3_000.0


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
            research_tools, workspace_tools = partition_tools_for_agents(all_tools)

            prompt_provider = FilePromptRegistry(
                assets_dir=settings.resolve_prompt_assets_dir(),
                registry_path=settings.resolve_prompt_registry_path(),
            )

            supervisor_subgraph = build_supervisor_graph(
                llm,
                research_tools,
                workspace_tools,
                prompt_provider=prompt_provider,
                researcher_llm=researcher_llm,
            ).compile()

            master = StateGraph(SupervisorState)
            master.add_node("supervisor", supervisor_subgraph)
            master.add_node("error_handler", error_handler_node)

            master.set_entry_point("supervisor")
            master.add_edge("supervisor", "error_handler")
            master.add_edge("error_handler", END)

            checkpointer = get_postgres_saver()
            self._compiled = master.compile(checkpointer=checkpointer)
            logger.info("Master agent graph compiled successfully (with checkpointer)")
            return self._compiled
        except Exception as exc:
            raise GraphCompilationError(detail=str(exc)) from exc

    # ── helpers (LangGraph-specific, kept private) ───────────────

    @staticmethod
    def _build_initial_state(
        user_message: str,
        session_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        return {
            "messages": [HumanMessage(content=user_message)],
            "session_id": session_id,
            "user_id": user_id,
            "error": None,
            "human_feedback": None,
            "next_agent": None,
            "delegation_reasoning": None,
        }

    @staticmethod
    def _config_for(thread_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": thread_id}}

    async def _result_from(
        self,
        graph: CompiledStateGraph,
        config: dict[str, Any],
        state: Any,
        *,
        thread_id: str,
    ) -> AgentRunResult:
        snapshot = await graph.aget_state(config)
        return to_run_result(state, snapshot, thread_id=thread_id)

    # ── IAgentOrchestrator implementation ────────────────────────

    async def invoke(
        self,
        user_message: str,
        *,
        session_id: str,
        user_id: str,
    ) -> AgentRunResult:
        started = perf_counter()
        await ensure_checkpointer_ready()
        graph = self._compile()
        initial_state = self._build_initial_state(user_message, session_id, user_id)
        config = self._config_for(session_id)
        state = await graph.ainvoke(initial_state, config=config)
        result = await self._result_from(graph, config, state, thread_id=session_id)
        elapsed_ms = (perf_counter() - started) * 1000
        logger.info(
            "graph.invoke completed request_id=%s thread_id=%s interrupted=%s elapsed_ms=%.1f",
            get_request_id(),
            session_id,
            result.interrupted,
            elapsed_ms,
        )
        return result

    async def stream(
        self,
        user_message: str,
        *,
        session_id: str,
        user_id: str,
    ) -> AsyncIterator[AgentEvent]:
        started = perf_counter()
        last_event_at = started
        event_count = 0
        await ensure_checkpointer_ready()
        graph = self._compile()
        initial_state = self._build_initial_state(user_message, session_id, user_id)
        config = self._config_for(session_id)
        async for chunk in graph.astream(initial_state, config=config):
            for event in to_agent_events(chunk):
                now = perf_counter()
                event_count += 1
                delta_ms = (now - last_event_at) * 1000
                total_ms = (now - started) * 1000
                last_event_at = now
                logger.info(
                    (
                        "graph.stream event request_id=%s thread_id=%s idx=%d "
                        "node=%s delta_ms=%.1f total_ms=%.1f"
                    ),
                    get_request_id(),
                    session_id,
                    event_count,
                    event.node,
                    delta_ms,
                    total_ms,
                )
                if delta_ms >= SLOW_STEP_MS:
                    logger.warning(
                        "graph.stream slow_step request_id=%s thread_id=%s node=%s delta_ms=%.1f",
                        get_request_id(),
                        session_id,
                        event.node,
                        delta_ms,
                    )
                yield event
        total_ms = (perf_counter() - started) * 1000
        logger.info(
            "graph.stream completed request_id=%s thread_id=%s events=%d elapsed_ms=%.1f",
            get_request_id(),
            session_id,
            event_count,
            total_ms,
        )

    async def resume(
        self,
        *,
        thread_id: str,
        action: str,
        feedback: str | None = None,
    ) -> AgentRunResult:
        started = perf_counter()
        await ensure_checkpointer_ready()
        graph = self._compile()
        config = self._config_for(thread_id)

        snapshot = await graph.aget_state(config)
        if not snapshot_is_paused(snapshot):
            raise GraphNotInterruptedError()

        resume_value: dict[str, Any] = {"action": action}
        if feedback:
            resume_value["feedback"] = feedback

        state = await graph.ainvoke(Command(resume=resume_value), config=config)
        result = await self._result_from(graph, config, state, thread_id=thread_id)
        elapsed_ms = (perf_counter() - started) * 1000
        logger.info(
            (
                "graph.resume completed request_id=%s thread_id=%s "
                "action=%s interrupted=%s elapsed_ms=%.1f"
            ),
            get_request_id(),
            thread_id,
            action,
            result.interrupted,
            elapsed_ms,
        )
        return result

    async def get_state(self, *, thread_id: str) -> AgentStateSnapshot:
        await ensure_checkpointer_ready()
        graph = self._compile()
        config = self._config_for(thread_id)
        snapshot = await graph.aget_state(config)
        return to_state_snapshot(snapshot, thread_id=thread_id)
