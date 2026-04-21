"""Domain rules for tool results shown to the LLM (size limits, truncation notices).

Concrete numeric limits are injected from :class:`app.core.config.settings.Settings`;
defaults here document recommended baselines for production deployments.
"""

from __future__ import annotations

import json
from typing import Any

# Baselines — keep in sync with Settings defaults for discoverability.
DEFAULT_MAX_TOOL_OUTPUT_CHARS: int = 10_000


def truncate_tool_return(value: Any, max_chars: int) -> Any:
    """Shorten tool output before it becomes a ToolMessage (string or JSON-serialised).

    Non-string values are normalised to text so the model always sees a bounded payload.
    ``max_chars <= 0`` disables truncation (escape hatch for tests or emergency override).
    """
    if max_chars <= 0:
        return value
    if isinstance(value, str):
        return _truncate_plain_text(value, max_chars)
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        text = str(value)
    return _truncate_plain_text(text, max_chars)


def _truncate_plain_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    suffix = f"\n\n...[Truncated: {omitted} characters omitted]"
    head = max_chars - len(suffix)
    if head < 1:
        return suffix.strip()
    return text[:head] + suffix
