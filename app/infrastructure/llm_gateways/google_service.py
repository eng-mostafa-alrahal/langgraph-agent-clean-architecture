"""Thin wrapper around the LangChain Google Gemini integration."""

from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config.settings import get_settings


def build_google_chat(
    model: str = "gemini-2.5-flash",
    temperature: float = 0.0,
    streaming: bool = True,
) -> ChatGoogleGenerativeAI:
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature,
        streaming=streaming,
    )
