"""Thin wrapper around the LangChain Groq integration."""

from __future__ import annotations

from langchain_groq import ChatGroq

from app.core.config.settings import get_settings


def build_groq_chat(
    model: str = "openai/gpt-oss-120b",
    temperature: float = 0.0,
    streaming: bool = False,
) -> ChatGroq:
    settings = get_settings()
    return ChatGroq(
        model=model,
        api_key=settings.GROQ_API_KEY,
        temperature=temperature,
        streaming=streaming,
    )
