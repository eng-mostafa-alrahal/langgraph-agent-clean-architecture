"""Research tools — web search (Tavily) and RAG retrieval."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.retrievers import BaseRetriever
from pydantic import BaseModel, ConfigDict, Field

from app.modules.agent_orchestration.infrastructure.tools.base_tool import ProjectBaseTool

logger = logging.getLogger(__name__)


class _SearchInput(BaseModel):
    query: str = Field(description="The search query string.")


class WebSearchTool(ProjectBaseTool):
    """Searches the web via Tavily for up-to-date information."""

    name: str = "web_search"
    description: str = (
        "Search the web for current, real-time information (sports results, news, "
        "'yesterday' / 'today', live data). Use whenever the user needs facts that may "
        "have changed recently or are not in the knowledge base."
    )
    args_schema: type[BaseModel] = _SearchInput

    api_key: str = Field(exclude=True, repr=False)
    max_results: int = Field(default=5, exclude=True)

    def _execute(self, query: str, **_: Any) -> str:
        from tavily import TavilyClient

        client = TavilyClient(api_key=self.api_key)
        response = client.search(query, max_results=self.max_results)

        results = response.get("results", [])
        if not results:
            return "No web results found for this query."

        formatted: list[str] = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            content = r.get("content", "")
            formatted.append(f"[{i}] {title}\n    URL: {url}\n    {content}")

        return "\n\n".join(formatted)


class RAGSearchTool(ProjectBaseTool):
    """Searches the internal knowledge base using semantic similarity."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "rag_search"
    description: str = (
        "Search the internal knowledge base for relevant documents and domain-specific "
        "information. Use before web search when the question may relate to internal data."
    )
    args_schema: type[BaseModel] = _SearchInput

    retriever: BaseRetriever | None = Field(default=None, exclude=True)

    def _execute(self, query: str, **_: Any) -> str:
        if self.retriever is None:
            return "Knowledge base is not configured. No documents available for retrieval."

        docs = self.retriever.invoke(query)
        if not docs:
            return "No relevant documents found in the knowledge base."

        formatted: list[str] = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "unknown")
            formatted.append(f"[{i}] (source: {source})\n    {doc.page_content}")

        return "\n\n".join(formatted)
