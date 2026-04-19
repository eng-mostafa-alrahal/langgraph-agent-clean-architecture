"""DTO for rendered prompt assets (content + observability metadata)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RenderedPromptDTO(BaseModel):
    """Compiled prompt text plus frontmatter-derived metadata for tracing."""

    content: str = Field(..., description="Final system prompt text after Jinja render.")
    metadata: dict[str, object] = Field(
        default_factory=dict,
        description="YAML frontmatter (version, trace_tags, model_target, …).",
    )
