"""Researcher sub-graph — plan, search, validate, synthesize."""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.modules.agent_orchestration.domain.routing_rules.researcher_router import (
    route_researcher,
)
from app.modules.agent_orchestration.domain.states.researcher_state import ResearcherState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.config.prompt_factory import (
    build_researcher_prompt,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.tool_error_handler import (  # noqa: E501
    researcher_tool_execution_error,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.subgraphs.researcher.nodes.context_validator import (  # noqa: E501
    make_context_validator_node,
)

logger = logging.getLogger(__name__)


def _is_groq_tool_invocation_format_error(exc: BaseException) -> bool:
    s = str(exc).lower()
    return "tool_use_failed" in s or "failed to call a function" in s


def _route_after_plan(state: ResearcherState) -> str:
    """Send to tool execution only when the LLM actually requested tool calls."""
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "search"
    return "synthesize"


def build_researcher_graph(
    llm: BaseChatModel,
    tools: list[BaseTool],
) -> StateGraph:
    llm_with_tools = llm.bind_tools(tools)
    prompt = build_researcher_prompt()

    async def plan_search(state: ResearcherState) -> dict:
        chain = prompt | llm_with_tools
        base_messages = list(state["messages"])
        nudge = (
            "Important: invoke tools only via native tool_calls from the API "
            "(including any MCP tools "
            "prefixed like filesystem__…). "
            "Do not write <function=...>, </function>, or any XML-style tool syntax "
            "- Groq rejects that."
        )
        for attempt in range(2):
            try:
                msgs = (
                    base_messages if attempt == 0 else [*base_messages, HumanMessage(content=nudge)]
                )
                response = await chain.ainvoke({"messages": msgs})
                return {"messages": [response]}
            except Exception as exc:
                if attempt == 0 and _is_groq_tool_invocation_format_error(exc):
                    logger.warning("plan_search: retrying after Groq tool format error: %s", exc)
                    continue
                raise

    async def collect_context(state: ResearcherState) -> dict:
        """Extract the latest round of tool results into retrieved_context."""
        new_context: list[str] = []
        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage):
                new_context.append(str(msg.content))
            else:
                break
        return {"retrieved_context": list(reversed(new_context))}

    async def synthesize(state: ResearcherState) -> dict:
        context = state.get("retrieved_context", [])
        if context:
            tail = (
                f"Based on the following research:\n\n{chr(10).join(context)}\n\n"
                "Provide a comprehensive, well-structured answer to the user's question."
            )
        else:
            tail = (
                "No tool results were returned this turn. Answer using the conversation and "
                "your general knowledge. If the question depends on very recent facts you cannot "
                "know for certain, give a careful answer and mention uncertainty "
                "briefly - do not refuse outright "
                "unless you truly have no relevant information."
            )
        # Keep full thread so model still sees the original user question.
        messages = [*list(state["messages"]), HumanMessage(content=tail)]
        response = await llm.ainvoke(messages)
        return {"messages": [AIMessage(content=str(response.content))]}

    tool_node = ToolNode(tools, handle_tool_errors=researcher_tool_execution_error)

    graph = StateGraph(ResearcherState)
    graph.add_node("plan_search", plan_search)
    graph.add_node("search", tool_node)
    graph.add_node("collect_context", collect_context)
    graph.add_node("validate_context", make_context_validator_node(llm))
    graph.add_node("synthesize", synthesize)

    graph.set_entry_point("plan_search")

    graph.add_conditional_edges(
        "plan_search",
        _route_after_plan,
        {
            "search": "search",
            "synthesize": "synthesize",
        },
    )
    graph.add_edge("search", "collect_context")
    graph.add_edge("collect_context", "validate_context")
    graph.add_conditional_edges(
        "validate_context",
        route_researcher,
        {
            "search": "plan_search",
            "synthesize": "synthesize",
            "end": END,
        },
    )
    graph.add_edge("synthesize", END)

    return graph
