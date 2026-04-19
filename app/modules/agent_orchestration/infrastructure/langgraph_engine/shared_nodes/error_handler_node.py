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
                AIMessage(
                    content="Something glitched on our side—mind trying once more?"
                )
            ],
            "error": None,
        }
    # No error: do not re-emit full state (would duplicate supervisor output in astream).
    return {}
