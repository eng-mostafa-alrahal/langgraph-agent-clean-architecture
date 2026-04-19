"""Background tasks that execute LangGraph runs outside the HTTP request cycle."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def execute_agent_graph(
    self,
    user_message: str,
    session_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Run the agent graph as a Celery task (for long-running or async-deferred work)."""
    from app.api.dependencies import _get_orchestrator

    try:
        orchestrator = _get_orchestrator()
        result = _run_async(
            orchestrator.invoke(user_message, session_id=session_id, user_id=user_id)
        )
        messages = result.get("messages", [])
        return {"reply": messages[-1].content if messages else ""}
    except Exception as exc:
        logger.exception("Agent task failed")
        raise self.retry(exc=exc) from exc
