"""Thin wrapper around the LangChain OpenAI integration."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config.settings import get_settings


def build_openai_chat(
    model: str | None = None,
    temperature: float = 0.0,
    streaming: bool = True,
) -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=model or settings.DEFAULT_MODEL_NAME,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
        streaming=streaming,
    )
