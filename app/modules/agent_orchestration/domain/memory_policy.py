"""Domain policy for when and how conversation history should be summarized."""

from __future__ import annotations


def should_summarize_messages(
    total_messages: int,
    *,
    trigger_threshold: int,
    keep_recent_messages: int,
) -> bool:
    """Return True when history should be compressed into a summary message."""
    if trigger_threshold <= 0:
        return False
    if keep_recent_messages < 1:
        return False
    return total_messages > max(trigger_threshold, keep_recent_messages + 1)


def summary_cut_index(total_messages: int, *, keep_recent_messages: int) -> int:
    """Number of oldest messages to summarize (prefix length)."""
    if keep_recent_messages < 1:
        return 0
    return max(0, total_messages - keep_recent_messages)
