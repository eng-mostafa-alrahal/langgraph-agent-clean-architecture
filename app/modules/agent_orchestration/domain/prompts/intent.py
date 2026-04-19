"""Stable prompt intents — resolved to concrete assets by infrastructure."""

from __future__ import annotations

from enum import StrEnum


class PromptIntent(StrEnum):
    """What kind of instructions the orchestration layer needs from the provider."""

    SUPERVISOR_ROUTING = "supervisor_routing"
    RESEARCHER_AGENT = "researcher_agent"
    WORKSPACE_AGENT = "workspace_agent"
    CHAT_AGENT = "chat_agent"
    STRUCTURED_OUTPUT_SYSTEM = "structured_output_system"
    RESEARCHER_CONTEXT_VALIDATION = "researcher_context_validation"
    WORKSPACE_CONTEXT_VALIDATION = "workspace_context_validation"
