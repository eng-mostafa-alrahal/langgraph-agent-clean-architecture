"""Grounding snippets for prompts that invoke an LLM without MessagesPlaceholder."""

from __future__ import annotations

from langchain_core.messages import HumanMessage


def recent_human_turns_as_text(
    messages: object,
    *,
    max_turns: int = 3,
    max_chars: int = 4000,
) -> str:
    """Concatenate the last N human messages so validators can see the user's ask."""
    if not isinstance(messages, list):
        return ""
    texts: list[str] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            c = msg.content
            texts.append(c if isinstance(c, str) else str(c))
    if not texts:
        return ""
    chunk = "\n---\n".join(texts[-max_turns:])
    return chunk[:max_chars]
