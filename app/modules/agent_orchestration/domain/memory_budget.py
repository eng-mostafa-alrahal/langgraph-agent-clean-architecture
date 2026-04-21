"""Declarative defaults for conversational memory budgets.

Application wiring should read overrides from :class:`app.core.config.settings.Settings`
and pass them into LangGraph adapters (trimming, routing-only windows, etc.).
"""

from __future__ import annotations

# Approximate tokenizer units used by LangChain's ``trim_messages(..., token_counter="approximate")``.
DEFAULT_AGENT_MAX_CONTEXT_TOKENS: int = 12_000

# Supervisor routing only needs recent intent — keep this small for latency and cost.
DEFAULT_SUPERVISOR_ROUTING_MAX_TOKENS: int = 2_048
