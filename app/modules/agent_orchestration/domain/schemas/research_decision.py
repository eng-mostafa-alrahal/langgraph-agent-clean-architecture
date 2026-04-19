"""Structured output schemas for LLM-produced decisions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchDecision(BaseModel):
    """The LLM outputs this to decide whether more research is needed."""

    model_config = ConfigDict(extra="ignore")

    needs_more_research: bool = Field(
        ..., description="Whether additional search queries are required."
    )
    search_queries: list[str] = Field(
        default_factory=list,
        description="Follow-up queries to run if more research is needed.",
    )
    reasoning: str = Field(
        default="",
        description="Brief justification for the decision.",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_llm_field_aliases(cls, data: Any) -> Any:
        """Groq json_mode often returns different key names than our schema."""
        if not isinstance(data, dict):
            return data
        d = dict(data)

        if "needs_more_research" not in d:
            if "sufficient_context" in d:
                d["needs_more_research"] = not bool(d.get("sufficient_context"))
            elif "needs_more_search" in d:
                d["needs_more_research"] = bool(d.get("needs_more_search"))
            elif d.get("follow_up_search_queries"):
                d["needs_more_research"] = True

        sq = d.get("search_queries")
        if sq is None:
            sq = []
        if not sq:
            for alt in ("follow_up_search_queries", "queries", "additional_search_queries"):
                raw = d.get(alt)
                if raw:
                    d["search_queries"] = list(raw) if isinstance(raw, list) else [str(raw)]
                    break
            else:
                d["search_queries"] = []
        else:
            d["search_queries"] = list(sq) if isinstance(sq, list) else [str(sq)]

        r = d.get("reasoning") or d.get("explanation") or d.get("justification")
        d["reasoning"] = str(r).strip() if r else "No reasoning provided."

        if "needs_more_research" not in d:
            d["needs_more_research"] = bool(d.get("search_queries"))

        return d


class WorkspaceLoopDecision(BaseModel):
    """Whether another tool-execution round is needed in the workspace subgraph."""

    model_config = ConfigDict(extra="ignore")

    needs_more_tool_calls: bool = Field(
        ...,
        description="Whether another planning/tool round is required before summarizing.",
    )
    follow_up_hints: list[str] = Field(
        default_factory=list,
        description="Short hints for the next planner turn (which tools or checks to run).",
    )
    reasoning: str = Field(
        default="",
        description="Brief justification.",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_llm_field_aliases(cls, data: Any) -> Any:
        """Groq json_mode often returns different key names; accept research-shaped aliases."""
        if not isinstance(data, dict):
            return data
        d = dict(data)

        if "needs_more_tool_calls" not in d:
            if "needs_more_research" in d:
                d["needs_more_tool_calls"] = bool(d.get("needs_more_research"))
            elif "sufficient_context" in d:
                d["needs_more_tool_calls"] = not bool(d.get("sufficient_context"))
            elif "needs_more_search" in d:
                d["needs_more_tool_calls"] = bool(d.get("needs_more_search"))
            elif d.get("follow_up_hints") or d.get("search_queries"):
                d["needs_more_tool_calls"] = True

        hints = d.get("follow_up_hints")
        if hints is None:
            hints = []
        if not hints:
            for alt in (
                "search_queries",
                "follow_up_search_queries",
                "queries",
                "additional_search_queries",
            ):
                raw = d.get(alt)
                if raw:
                    d["follow_up_hints"] = list(raw) if isinstance(raw, list) else [str(raw)]
                    break
            else:
                d["follow_up_hints"] = []
        else:
            d["follow_up_hints"] = list(hints) if isinstance(hints, list) else [str(hints)]

        r = d.get("reasoning") or d.get("explanation") or d.get("justification")
        d["reasoning"] = str(r).strip() if r else "No reasoning provided."

        if "needs_more_tool_calls" not in d:
            d["needs_more_tool_calls"] = bool(d.get("follow_up_hints"))

        return d


class DelegationDecision(BaseModel):
    """The supervisor LLM outputs this to delegate to a sub-agent."""

    next_agent: str = Field(
        ...,
        description=(
            "Which specialist to delegate to: 'researcher' (web/RAG/time), "
            "'workspace' (extended/MCP tools — filesystem and future integrations, if "
            "registered), 'chat', or 'end'."
        ),
    )
    reasoning: str = Field(..., description="Brief justification for the delegation choice.")
