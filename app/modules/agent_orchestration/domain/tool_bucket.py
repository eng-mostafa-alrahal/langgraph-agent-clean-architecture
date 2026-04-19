"""Which subgraph may bind a registered tool (selective sharing)."""

from __future__ import annotations

from enum import StrEnum


class AgentToolBucket(StrEnum):
    """Execution slots that call ``bind_tools`` — not user-facing agent names."""

    RESEARCHER = "researcher"
    WORKSPACE = "workspace"
