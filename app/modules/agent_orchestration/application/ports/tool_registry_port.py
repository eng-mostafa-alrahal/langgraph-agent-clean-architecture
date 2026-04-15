"""Contract for a registry that resolves LangChain tools by name."""

from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.tools import BaseTool


class IToolRegistry(ABC):
    @abstractmethod
    def get_tools(self, tool_names: list[str]) -> list[BaseTool]:
        """Return tool instances matching the requested names."""
        ...

    @abstractmethod
    def list_available(self) -> list[str]:
        """Return names of all registered tools."""
        ...
