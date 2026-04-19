"""Port for resolving prompt intents to rendered text — implemented in infrastructure."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.agent_orchestration.application.dtos.prompt_dto import RenderedPromptDTO
from app.modules.agent_orchestration.domain.prompts.context import PromptContext
from app.modules.agent_orchestration.domain.prompts.intent import PromptIntent


class IPromptProvider(ABC):
    """Loads and composes prompt assets without LangChain types on the interface."""

    @abstractmethod
    def resolve_prompt(self, intent: PromptIntent, context: PromptContext) -> RenderedPromptDTO:
        """Return rendered body and metadata for the given intent."""
