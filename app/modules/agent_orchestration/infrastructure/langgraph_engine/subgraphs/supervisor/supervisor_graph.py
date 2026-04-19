"""Supervisor sub-graph — analyses intent and delegates to specialists."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

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
    researcher_llm: BaseChatModel | None = None,
) -> StateGraph:
    tool_llm = researcher_llm if researcher_llm is not None else llm
    include_workspace_agent = len(workspace_tools) > 0
    researcher_subgraph = build_researcher_graph(tool_llm, research_tools).compile()
    workspace_subgraph = build_workspace_graph(tool_llm, workspace_tools).compile()

    graph = StateGraph(SupervisorState)
    graph.add_node(
        "delegate",
        make_task_delegator_node(llm, include_workspace_agent=include_workspace_agent),
    )
    graph.add_node("human_review", human_review_node)
    graph.add_node("researcher", researcher_subgraph)
    graph.add_node("workspace", workspace_subgraph)
    graph.add_node("chat", make_chat_node(llm))

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

    graph.add_edge("researcher", END)
    graph.add_edge("workspace", END)
    graph.add_edge("chat", END)

    return graph
