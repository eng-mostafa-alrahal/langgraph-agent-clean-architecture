"""Global error-handling node — catches unhandled exceptions in the graph."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)


async def error_handler_node(state: dict[str, Any]) -> dict[str, Any]:
    error = state.get("error")
    if error:
        logger.error("Agent graph error: %s", error)
        return {
            "messages": [
                AIMessage(content="I encountered an issue processing your request. Please try again.")
            ],
            "error": None,
        }
    return state
