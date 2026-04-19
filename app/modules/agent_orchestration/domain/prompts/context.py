"""Variables passed into Jinja when rendering a prompt asset."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PromptContext(BaseModel):
    """Template variables for supervisor routing (and future intents)."""

    model_config = ConfigDict(extra="allow")

    compact_schema: str = Field(
        default="",
        description="Human-readable summary of the expected structured output fields.",
    )
    include_workspace_agent: bool = Field(
        default=False,
        description="When True, workspace appears as a routable specialist.",
    )
    goal_section: str = Field(
        default="",
        description="Optional preamble with recent user turns (validators).",
    )
    retrieved_evidence: str = Field(
        default="",
        description="Joined tool outputs for validation rounds.",
    )
