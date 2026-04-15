"""Thin wrapper around the LangChain Anthropic integration."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic

from app.core.config.settings import get_settings


def build_anthropic_chat(
    model: str = "claude-sonnet-4-20250514",
    temperature: float = 0.0,
    streaming: bool = True,
) -> ChatAnthropic:
    settings = get_settings()
    return ChatAnthropic(
        model_name=model,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=temperature,
        streaming=streaming,
    )
