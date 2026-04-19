"""LangChain RunnableConfig snippets for LangSmith prompt correlation."""

from __future__ import annotations

import json
from typing import Any


def trace_run_config_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Build ``ainvoke`` / ``invoke`` config with tags and flat metadata for tracing."""
    tags: list[str] = []
    intent = metadata.get("intent")
    version = metadata.get("version")
    if isinstance(intent, str) and intent:
        tags.append(f"prompt_intent:{intent}")
    if isinstance(version, str) and version:
        tags.append(f"prompt_version:{version}")
    trace_tags = metadata.get("trace_tags")
    if isinstance(trace_tags, dict):
        for k, v in trace_tags.items():
            tags.append(f"{k}:{v}")

    flat_meta: dict[str, Any] = {}
    for key, val in metadata.items():
        if isinstance(val, dict):
            flat_meta[key] = json.dumps(val, ensure_ascii=False)
        elif isinstance(val, (str, int, float, bool)) or val is None:
            flat_meta[key] = val
        else:
            flat_meta[key] = str(val)

    return {"tags": tags, "metadata": flat_meta}


def trace_config_for_structured_pair(
    system_metadata: dict[str, Any],
    human_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Trace config for `SystemMessage` + `HumanMessage` prompt pair (shared system + body)."""
    cfg = trace_run_config_from_metadata(human_metadata)
    tags: list[str] = list(cfg.get("tags") or [])
    ap = system_metadata.get("asset_path")
    if isinstance(ap, str) and ap:
        tags.append(f"prompt_system_asset:{ap}")
    out = dict(cfg)
    out["tags"] = tags
    return out
