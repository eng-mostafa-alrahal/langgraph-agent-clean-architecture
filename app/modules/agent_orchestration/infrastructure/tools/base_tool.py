"""Base class for project-specific LangChain tools with shared boilerplate."""

from __future__ import annotations

import logging
from abc import abstractmethod
from time import perf_counter
from typing import Any

from langchain_core.tools import BaseTool as _LCBaseTool
from pydantic import Field

from app.core.observability.request_context import get_request_id

logger = logging.getLogger(__name__)
SLOW_TOOL_MS = 2_000.0


class ProjectBaseTool(_LCBaseTool):
    """All custom tools inherit from this to gain consistent logging & error handling."""

    verbose: bool = Field(default=False)

    @abstractmethod
    def _execute(self, *args: Any, **kwargs: Any) -> Any: ...

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        started = perf_counter()
        try:
            logger.info("Running tool %s", self.name)
            result = self._execute(*args, **kwargs)
            elapsed_ms = (perf_counter() - started) * 1000
            logger.info(
                "tool.run succeeded request_id=%s tool=%s elapsed_ms=%.1f",
                get_request_id(),
                self.name,
                elapsed_ms,
            )
            if elapsed_ms >= SLOW_TOOL_MS:
                logger.warning(
                    "tool.run slow request_id=%s tool=%s elapsed_ms=%.1f",
                    get_request_id(),
                    self.name,
                    elapsed_ms,
                )
            return result
        except Exception:
            elapsed_ms = (perf_counter() - started) * 1000
            logger.exception(
                "tool.run failed request_id=%s tool=%s elapsed_ms=%.1f",
                get_request_id(),
                self.name,
                elapsed_ms,
            )
            raise
