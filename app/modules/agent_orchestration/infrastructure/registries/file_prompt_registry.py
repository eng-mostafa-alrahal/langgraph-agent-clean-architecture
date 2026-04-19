"""Loads Markdown/Jinja prompt assets using a TOML intent registry."""

from __future__ import annotations

import logging
import re
import tomllib
from pathlib import Path
from typing import Any

import yaml
from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment

from app.modules.agent_orchestration.application.dtos.prompt_dto import RenderedPromptDTO
from app.modules.agent_orchestration.application.ports.prompt_provider_port import IPromptProvider
from app.modules.agent_orchestration.domain.prompts.context import PromptContext
from app.modules.agent_orchestration.domain.prompts.intent import PromptIntent

logger = logging.getLogger(__name__)

_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*\r?\n", re.DOTALL)


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Parse optional YAML frontmatter; return (metadata, body_without_frontmatter)."""
    match = _FRONTMATTER_PATTERN.match(raw)
    if not match:
        return {}, raw
    yaml_block = match.group(1)
    body = raw[match.end() :]
    meta = yaml.safe_load(yaml_block)
    if meta is None:
        return {}, body
    if not isinstance(meta, dict):
        logger.warning("prompt_frontmatter_not_mapping intent_data=%s", type(meta).__name__)
        return {}, body
    return meta, body


class FilePromptRegistry(IPromptProvider):
    """Resolve :class:`PromptIntent` via ``prompt_registry.toml`` and Jinja templates."""

    def __init__(
        self,
        *,
        assets_dir: Path,
        registry_path: Path,
    ) -> None:
        self._assets_dir = assets_dir.resolve()
        self._registry_path = registry_path.resolve()
        self._intent_paths = self._load_registry(self._registry_path)
        self._env = SandboxedEnvironment(
            loader=FileSystemLoader(str(self._assets_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @staticmethod
    def _load_registry(path: Path) -> dict[str, str]:
        raw = path.read_text(encoding="utf-8")
        data = tomllib.loads(raw)
        intents = data.get("intents")
        if not isinstance(intents, dict):
            raise ValueError(f"prompt_registry missing [intents] table: {path}")
        result: dict[str, str] = {}
        for key, rel in intents.items():
            if isinstance(rel, str) and rel.strip():
                result[str(key)] = rel.strip()
        return result

    def resolve_prompt(self, intent: PromptIntent, context: PromptContext) -> RenderedPromptDTO:
        key = intent.value
        relative = self._intent_paths.get(key)
        if relative is None:
            raise KeyError(f"No prompt asset registered for intent '{key}'")

        source_path = self._assets_dir / relative
        if not source_path.is_file():
            raise FileNotFoundError(f"Prompt asset not found: {source_path}")

        raw_text = source_path.read_text(encoding="utf-8")
        meta, template_body = _split_frontmatter(raw_text)

        template = self._env.from_string(template_body)
        rendered_body = template.render(**context.model_dump())

        merged_meta: dict[str, object] = {
            **{k: v for k, v in meta.items()},
            "intent": key,
            "asset_path": relative,
        }

        return RenderedPromptDTO(content=rendered_body.strip(), metadata=merged_meta)
