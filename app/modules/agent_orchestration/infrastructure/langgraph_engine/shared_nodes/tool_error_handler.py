"""LangGraph ToolNode error handling — graceful recovery for MCP / runtime failures."""

from __future__ import annotations

from langchain_core.tools import ToolException


def researcher_tool_execution_error(exc: Exception) -> str:
    """Return a safe tool error string for the LLM (never raises).

    Annotated as ``Exception`` so LangGraph treats this handler as catching all
    execution failures while leaving GraphBubbleUp / interrupts untouched (they
    are not subclasses of Exception).
    """
    if isinstance(exc, ToolException):
        return (
            "Error: Tool execution failed "
            f"({type(exc).__name__}). {exc!s} "
            "Please use an alternative tool or ask the user for guidance."
        )

    return (
        "Error: Tool execution failed "
        f"({type(exc).__name__}). The tool may be unavailable, misconfigured, or rejected "
        "by an external MCP server. Please use an alternative tool or ask the user for guidance."
    )
