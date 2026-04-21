"""Supervisor sub-graph — analyses intent and delegates to specialists."""

from __future__ import annotations

from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from app.modules.agent_orchestration.application.ports.prompt_provider_port import IPromptProvider
from app.modules.agent_orchestration.domain.memory_policy import should_summarize_messages
from app.modules.agent_orchestration.domain.routing_rules.approval_router import (
    route_after_human_review,
    route_to_human_review,
)
from app.modules.agent_orchestration.domain.states.supervisor_state import SupervisorState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.chat_node import (
    make_chat_node,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.human_review_node import (  # noqa: E501
    human_review_node,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.memory_manager_node import (  # noqa: E501
    make_memory_manager_node,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.subgraphs.researcher.researcher_graph import (  # noqa: E501
    build_researcher_graph,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.subgraphs.supervisor.nodes.task_delegator import (  # noqa: E501
    make_task_delegator_node,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.subgraphs.workspace.workspace_graph import (  # noqa: E501
    build_workspace_graph,
)


def build_supervisor_graph(
    llm: BaseChatModel,
    research_tools: list[BaseTool],
    workspace_tools: list[BaseTool],
    *,
    prompt_provider: IPromptProvider,
    researcher_llm: BaseChatModel | None = None,
    agent_max_context_tokens: int,
    supervisor_routing_max_tokens: int,
    max_tool_output_chars: int,
    memory_trigger_messages: int,
    memory_keep_recent_messages: int,
    memory_summary_max_chars: int,
    memory_llm: BaseChatModel,
) -> StateGraph:
    tool_llm = researcher_llm if researcher_llm is not None else llm
    include_workspace_agent = len(workspace_tools) > 0
    researcher_subgraph = build_researcher_graph(
        tool_llm,
        research_tools,
        prompt_provider=prompt_provider,
        max_context_tokens=agent_max_context_tokens,
        max_tool_output_chars=max_tool_output_chars,
    ).compile()
    workspace_subgraph = build_workspace_graph(
        tool_llm,
        workspace_tools,
        prompt_provider=prompt_provider,
        max_context_tokens=agent_max_context_tokens,
        max_tool_output_chars=max_tool_output_chars,
    ).compile()

    graph = StateGraph(SupervisorState)
    graph.add_node(
        "delegate",
        make_task_delegator_node(
            llm,
            prompt_provider=prompt_provider,
            include_workspace_agent=include_workspace_agent,
            routing_max_tokens=supervisor_routing_max_tokens,
        ),
    )
    graph.add_node("human_review", human_review_node)
    graph.add_node(
        "memory_manager",
        make_memory_manager_node(
            memory_llm,
            keep_recent_messages=memory_keep_recent_messages,
            summary_max_chars=memory_summary_max_chars,
        ),
    )
    graph.add_node("researcher", researcher_subgraph)
    graph.add_node("workspace", workspace_subgraph)
    graph.add_node(
        "chat",
        make_chat_node(
            llm,
            prompt_provider=prompt_provider,
            max_context_tokens=agent_max_context_tokens,
        ),
    )

    graph.set_entry_point("delegate")

    graph.add_conditional_edges(
        "delegate",
        route_to_human_review,
        {
            "human_review": "human_review",
            "researcher": "researcher",
            "chat": "chat",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "researcher": "researcher",
            "workspace": "workspace",
            "chat": "chat",
            "end": END,
        },
    )
    def route_post_reply(state: SupervisorState) -> Literal["memory_manager", "end"]:
        total = len(state.get("messages", []))
        if should_summarize_messages(
            total,
            trigger_threshold=memory_trigger_messages,
            keep_recent_messages=memory_keep_recent_messages,
        ):
            return "memory_manager"
        return "end"

    graph.add_conditional_edges(
        "researcher",
        route_post_reply,
        {"memory_manager": "memory_manager", "end": END},
    )
    graph.add_conditional_edges(
        "workspace",
        route_post_reply,
        {"memory_manager": "memory_manager", "end": END},
    )
    graph.add_conditional_edges(
        "chat",
        route_post_reply,
        {"memory_manager": "memory_manager", "end": END},
    )
    graph.add_edge("memory_manager", END)

    return graph
