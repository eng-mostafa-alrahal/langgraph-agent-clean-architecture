"""Contract for a registry that resolves LLM chat-model instances by name."""

from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel


class ILLMRegistry(ABC):
    @abstractmethod
    def get_model(self, provider: str, model_name: str | None = None) -> BaseChatModel:
        """Return a configured chat-model for the given provider/model pair."""
        ...
