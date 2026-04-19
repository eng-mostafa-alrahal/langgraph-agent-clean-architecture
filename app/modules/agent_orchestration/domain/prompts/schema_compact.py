"""Compress Pydantic JSON Schema for inclusion in system prompts (token-aware)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def compact_schema_for_llm(model: type[BaseModel]) -> str:
    """Summarise top-level fields with types, optionality, and descriptions."""
    schema = model.model_json_schema()
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return "(no fields)"

    required = set(schema.get("required") or [])
    lines: list[str] = []
    for name in sorted(properties.keys()):
        spec_any = properties[name]
        if not isinstance(spec_any, dict):
            lines.append(f"- {name}: (see schema)")
            continue
        spec: dict[str, Any] = spec_any
        typ = _type_hint(spec)
        desc = str(spec.get("description", "")).strip().replace("\n", " ")
        req = "required" if name in required else "optional"
        tail = f" — {desc}" if desc else ""
        lines.append(f"- {name} ({typ}, {req}){tail}")
    return "\n".join(lines)


def _type_hint(spec: dict[str, Any]) -> str:
    t = spec.get("type")
    if isinstance(t, list):
        return " | ".join(str(x) for x in t)
    if t:
        return str(t)
    if "anyOf" in spec:
        parts = []
        for branch in spec["anyOf"]:
            if isinstance(branch, dict) and branch.get("type"):
                parts.append(str(branch["type"]))
        if parts:
            return " | ".join(parts)
    return "any"
