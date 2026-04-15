"""Base class for project-specific LangChain tools with shared boilerplate."""

from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any

from langchain_core.tools import BaseTool as _LCBaseTool
from pydantic import Field

logger = logging.getLogger(__name__)


class ProjectBaseTool(_LCBaseTool):
    """All custom tools inherit from this to gain consistent logging & error handling."""

    verbose: bool = Field(default=False)

    @abstractmethod
    def _execute(self, *args: Any, **kwargs: Any) -> Any: ...

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        try:
            logger.info("Running tool %s", self.name)
            return self._execute(*args, **kwargs)
        except Exception:
            logger.exception("Tool %s failed", self.name)
            raise
