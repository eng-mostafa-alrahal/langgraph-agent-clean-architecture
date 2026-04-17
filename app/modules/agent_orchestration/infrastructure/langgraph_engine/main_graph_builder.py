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
from langgraph.types import Command

from app.core.config.settings import get_settings
from app.core.exceptions import GraphCompilationError
from app.modules.agent_orchestration.application.ports.agent_orchestrator_port import (
    IAgentOrchestrator,
)
from app.modules.agent_orchestration.application.ports.llm_registry_port import ILLMRegistry
from app.modules.agent_orchestration.application.ports.tool_registry_port import IToolRegistry
from app.modules.agent_orchestration.domain.states.supervisor_state import SupervisorState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.memory.postgres_saver import (
    ensure_checkpointer_ready,
    get_postgres_saver,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.error_handler_node import (
    error_handler_node,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.subgraphs.supervisor.supervisor_graph import (
    build_supervisor_graph,
)

logger = logging.getLogger(__name__)


def _snapshot_is_paused(snapshot: Any) -> bool:
    """True when the checkpoint is waiting for human resume.

    LangGraph may represent a pause either as ``snapshot.next`` (nodes to run) or
    as ``snapshot.interrupts`` / per-task interrupts with an empty ``next`` tuple.
    Only checking ``next`` incorrectly raises GRAPH_NOT_INTERRUPTED on newer runtimes.
    """
    if getattr(snapshot, "next", None):
        return True
    intr = getattr(snapshot, "interrupts", None) or ()
    if intr:
        return True
    for task in getattr(snapshot, "tasks", None) or ():
        if getattr(task, "interrupts", None):
            return True
    return False


def _interrupt_payload_from_snapshot(snapshot: Any) -> Any:
    """Best-effort payload passed to ``interrupt()`` for the pending gate."""
    intr = getattr(snapshot, "interrupts", None) or ()
    if intr:
        return intr[0].value
    for task in getattr(snapshot, "tasks", None) or ():
        t_intr = getattr(task, "interrupts", None) or ()
        if t_intr:
            return t_intr[0].value
    return None


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

            checkpointer = get_postgres_saver()
            self._compiled = master.compile(checkpointer=checkpointer)
            logger.info("Master agent graph compiled successfully (with checkpointer)")
            return self._compiled
        except Exception as exc:
            raise GraphCompilationError(detail=str(exc)) from exc

    # ── helpers ──────────────────────────────────────────────────

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

    async def _check_interrupted(
        self,
        graph: CompiledStateGraph,
        config: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Attach interrupt metadata to *result* when the graph is paused."""
        snapshot = await graph.aget_state(config)
        if _snapshot_is_paused(snapshot):
            result["__interrupted"] = True
            result["__interrupt_payload"] = _interrupt_payload_from_snapshot(snapshot)
        return result

    # ── IAgentOrchestrator implementation ────────────────────────

    async def invoke(
        self,
        user_message: str,
        *,
        session_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        await ensure_checkpointer_ready()
        graph = self._compile()
        initial_state = self._build_initial_state(user_message, session_id, user_id)
        config = {"configurable": {"thread_id": session_id}}
        result = await graph.ainvoke(initial_state, config=config)
        return await self._check_interrupted(graph, config, result)

    async def stream(
        self,
        user_message: str,
        *,
        session_id: str,
        user_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        await ensure_checkpointer_ready()
        graph = self._compile()
        initial_state = self._build_initial_state(user_message, session_id, user_id)
        config = {"configurable": {"thread_id": session_id}}
        async for event in graph.astream(initial_state, config=config):
            yield event

    async def resume(
        self,
        *,
        thread_id: str,
        action: str,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        await ensure_checkpointer_ready()
        graph = self._compile()
        config = {"configurable": {"thread_id": thread_id}}

        snapshot = await graph.aget_state(config)
        if not _snapshot_is_paused(snapshot):
            from app.core.exceptions import GraphNotInterruptedError

            raise GraphNotInterruptedError()

        resume_value: dict[str, Any] = {"action": action}
        if feedback:
            resume_value["feedback"] = feedback

        result = await graph.ainvoke(Command(resume=resume_value), config=config)
        return await self._check_interrupted(graph, config, result)

    async def get_state(self, *, thread_id: str) -> Any:
        await ensure_checkpointer_ready()
        graph = self._compile()
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await graph.aget_state(config)
        return {
            "values": snapshot.values,
            "next": list(snapshot.next) if snapshot.next else [],
            "interrupted": _snapshot_is_paused(snapshot),
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "interrupts": [
                        {"value": i.value} for i in (t.interrupts or [])
                    ],
                }
                for t in (snapshot.tasks or [])
            ],
        }
