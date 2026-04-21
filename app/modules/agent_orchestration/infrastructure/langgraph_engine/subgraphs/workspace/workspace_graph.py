"""Workspace-tools sub-graph — plan, run extended (non-research) tools, validate, summarize."""

from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.modules.agent_orchestration.application.ports.prompt_provider_port import IPromptProvider
from app.modules.agent_orchestration.domain.prompts.context import PromptContext
from app.modules.agent_orchestration.domain.prompts.intent import PromptIntent
from app.modules.agent_orchestration.domain.routing_rules.researcher_router import (
    route_researcher,
)
from app.modules.agent_orchestration.domain.states.researcher_state import ResearcherState
from app.modules.agent_orchestration.infrastructure.langgraph_engine.mappers.prompt_mapper import (
    to_chat_prompt_template,
    trim_conversation_messages,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.prompt_trace_config import (
    trace_run_config_from_metadata,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.shared_nodes.tool_error_handler import (  # noqa: E501
    researcher_tool_execution_error,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.tool_output_cap import (
    tool_call_truncators,
)
from app.modules.agent_orchestration.infrastructure.langgraph_engine.subgraphs.workspace.nodes.context_validator import (  # noqa: E501
    make_workspace_context_validator_node,
)

logger = logging.getLogger(__name__)


def _is_tool_invocation_format_error(exc: BaseException) -> bool:
    s = str(exc).lower()
    return "tool_use_failed" in s or "failed to call a function" in s


def _route_after_plan(state: ResearcherState) -> str:
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return "synthesize"


def build_workspace_graph(
    llm: BaseChatModel,
    tools: list[BaseTool],
    *,
    prompt_provider: IPromptProvider,
    max_context_tokens: int,
    max_tool_output_chars: int,
) -> StateGraph:
    llm_with_tools = llm.bind_tools(tools)
    rendered = prompt_provider.resolve_prompt(PromptIntent.WORKSPACE_AGENT, PromptContext())
    prompt = to_chat_prompt_template(rendered)
    trace_cfg = trace_run_config_from_metadata(rendered.metadata)
    logger.info(
        "workspace_prompt_loaded intent=%s version=%s asset=%s",
        rendered.metadata.get("intent"),
        rendered.metadata.get("version"),
        rendered.metadata.get("asset_path"),
    )

    async def plan_tools(state: ResearcherState) -> dict:
        chain = prompt | llm_with_tools
        base_messages = trim_conversation_messages(
            state["messages"],
            max_tokens=max_context_tokens,
        )
        nudge = (
            "Important: invoke tools only via native tool_calls (e.g. MCP tools "
            "prefixed like servername__toolname). "
            "Do not write <function=...>, </function>, or any XML-style tool syntax."
        )
        for attempt in range(2):
            try:
                msgs = (
                    base_messages if attempt == 0 else [*base_messages, HumanMessage(content=nudge)]
                )
                response = await chain.ainvoke({"messages": msgs}, config=trace_cfg)
                return {"messages": [response]}
            except Exception as exc:
                if attempt == 0 and _is_tool_invocation_format_error(exc):
                    logger.warning("plan_tools: retrying after tool format error: %s", exc)
                    continue
                raise

    async def collect_context(state: ResearcherState) -> dict:
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
                f"Tool output for this step:\n\n{chr(10).join(context)}\n\n"
                "Tell the user what happened in a short, friendly message (like you're "
                "catching them up). Include specifics they care about "
                "(paths, errors, counts) without dumping a formal report."
            )
        else:
            tail = (
                "Nothing came back from tools this time. Tell them in one or two warm "
                "sentences and suggest what they could try next — no robotic disclaimer."
            )
        trimmed = trim_conversation_messages(
            state["messages"],
            max_tokens=max_context_tokens,
        )
        messages = [*trimmed, HumanMessage(content=tail)]
        response = await llm.ainvoke(messages)
        return {"messages": [AIMessage(content=str(response.content))]}

    sync_trunc, async_trunc = tool_call_truncators(max_tool_output_chars)
    _tool_kw: dict[str, object] = {"handle_tool_errors": researcher_tool_execution_error}
    if sync_trunc is not None and async_trunc is not None:
        _tool_kw["wrap_tool_call"] = sync_trunc
        _tool_kw["awrap_tool_call"] = async_trunc
    tool_node = ToolNode(tools, **_tool_kw)

    graph = StateGraph(ResearcherState)
    graph.add_node("plan_tools", plan_tools)
    graph.add_node("tools", tool_node)
    graph.add_node("collect_context", collect_context)
    graph.add_node(
        "validate_context",
        make_workspace_context_validator_node(llm, prompt_provider=prompt_provider),
    )
    graph.add_node("synthesize", synthesize)

    graph.set_entry_point("plan_tools")

    graph.add_conditional_edges(
        "plan_tools",
        _route_after_plan,
        {
            "tools": "tools",
            "synthesize": "synthesize",
        },
    )
    graph.add_edge("tools", "collect_context")
    graph.add_edge("collect_context", "validate_context")
    graph.add_conditional_edges(
        "validate_context",
        route_researcher,
        {
            "search": "plan_tools",
            "synthesize": "synthesize",
            "end": END,
        },
    )
    graph.add_edge("synthesize", END)

    return graph
