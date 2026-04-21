"""Concrete LLM registry — resolves provider/model pairs to chat-model instances."""

from __future__ import annotations

from typing import ClassVar

from langchain_core.language_models import BaseChatModel

from app.infrastructure.llm_gateways.anthropic_service import build_anthropic_chat
from app.infrastructure.llm_gateways.google_service import build_google_chat
from app.infrastructure.llm_gateways.openai_service import build_openai_chat
from app.modules.agent_orchestration.application.ports.llm_registry_port import ILLMRegistry


class LLMRegistry(ILLMRegistry):
    _builders: ClassVar[dict[str, object]] = {
        "openai": build_openai_chat,
        "anthropic": build_anthropic_chat,
        "gemini": build_google_chat,
    }

    def get_model(self, provider: str, model_name: str | None = None) -> BaseChatModel:
        builder = self._builders.get(provider)
        if builder is None:
            raise ValueError(f"Unknown LLM provider: {provider}")
        kwargs: dict[str, object] = {}
        if model_name:
            kwargs["model"] = model_name
        return builder(**kwargs)  # type: ignore[operator]
