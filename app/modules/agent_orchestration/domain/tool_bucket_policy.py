"""Declarative overrides: shared tools vs single-bucket defaults.

Default routing (when a name is **not** listed here) is defined in
``partition_tools_for_agents`` — built-ins go to the researcher bucket only,
everything else to the workspace bucket only.

Add a name here with **one or both** buckets to expose that tool on both subgraphs
(shared implementation, selective binding).
"""

from __future__ import annotations

from app.modules.agent_orchestration.domain.tool_bucket import AgentToolBucket

# Example (uncomment when you register a tool with this name):
# TOOL_BUCKET_OVERRIDES: dict[str, frozenset[AgentToolBucket]] = {
#     "get_local_time": frozenset({AgentToolBucket.RESEARCHER, AgentToolBucket.WORKSPACE}),
# }

TOOL_BUCKET_OVERRIDES: dict[str, frozenset[AgentToolBucket]] = {}
