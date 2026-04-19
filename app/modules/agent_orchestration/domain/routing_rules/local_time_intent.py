"""Detect user messages that need ``get_local_time`` (researcher), not plain chat."""

from __future__ import annotations

import re

_LOCAL_TIME_RE = re.compile(
    r"(?is)"
    r"(?:"
    r"\bwhat(?:'s|\s+is)\s+the\s+(?:current\s+)?time\s+(?:in|at)\b|"
    r"\bwhat\s+time\s+(?:is\s+it\s+)?(?:in|at)\b|"
    r"\b(?:current|local)\s+time\s+(?:in|at)\b"
    r")",
)


def looks_like_local_time_question(text: str) -> bool:
    """True when the message is asking for the clock time in a place (city/region)."""
    return bool(text and _LOCAL_TIME_RE.search(text.strip()))
