"""Tests for file-backed prompt registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config.settings import Settings
from app.modules.agent_orchestration.domain.prompts.context import PromptContext
from app.modules.agent_orchestration.domain.prompts.intent import PromptIntent
from app.modules.agent_orchestration.infrastructure.registries.file_prompt_registry import (
    FilePromptRegistry,
)


@pytest.fixture
def registry_paths() -> tuple[Path, Path]:
    settings = Settings()
    return settings.resolve_prompt_assets_dir(), settings.resolve_prompt_registry_path()


def test_resolve_supervisor_routing_renders(registry_paths: tuple[Path, Path]) -> None:
    assets_dir, registry_path = registry_paths
    reg = FilePromptRegistry(assets_dir=assets_dir, registry_path=registry_path)
    ctx = PromptContext(
        compact_schema="- next_agent (string, required)",
        include_workspace_agent=True,
    )
    dto = reg.resolve_prompt(PromptIntent.SUPERVISOR_ROUTING, ctx)
    assert "handling path" in dto.content.lower()
    assert dto.metadata.get("version") == "1.2"
    assert dto.metadata.get("intent") == "supervisor_routing"
    assert "workspace" in dto.content.lower()


def test_resolve_researcher_prompt_renders(registry_paths: tuple[Path, Path]) -> None:
    assets_dir, registry_path = registry_paths
    reg = FilePromptRegistry(assets_dir=assets_dir, registry_path=registry_path)
    dto = reg.resolve_prompt(PromptIntent.RESEARCHER_AGENT, PromptContext())
    assert "tools available in this session" in dto.content.lower()
    assert "{% raw %}" not in dto.content
    assert dto.metadata.get("intent") == "researcher_agent"


def test_structured_output_system_renders(registry_paths: tuple[Path, Path]) -> None:
    assets_dir, registry_path = registry_paths
    reg = FilePromptRegistry(assets_dir=assets_dir, registry_path=registry_path)
    dto = reg.resolve_prompt(PromptIntent.STRUCTURED_OUTPUT_SYSTEM, PromptContext())
    assert "json" in dto.content.lower()
    assert dto.metadata.get("intent") == "structured_output_system"


def test_researcher_context_validation_renders(registry_paths: tuple[Path, Path]) -> None:
    assets_dir, registry_path = registry_paths
    reg = FilePromptRegistry(assets_dir=assets_dir, registry_path=registry_path)
    dto = reg.resolve_prompt(
        PromptIntent.RESEARCHER_CONTEXT_VALIDATION,
        PromptContext(
            goal_section="User request (recent turns):\nhello\n\n",
            retrieved_evidence="snippet one",
            compact_schema="- needs_more_research",
        ),
    )
    assert "snippet one" in dto.content
    assert "needs_more_research" in dto.content.lower()
    assert dto.metadata.get("intent") == "researcher_context_validation"


def test_workspace_context_validation_renders(registry_paths: tuple[Path, Path]) -> None:
    assets_dir, registry_path = registry_paths
    reg = FilePromptRegistry(assets_dir=assets_dir, registry_path=registry_path)
    dto = reg.resolve_prompt(
        PromptIntent.WORKSPACE_CONTEXT_VALIDATION,
        PromptContext(
            retrieved_evidence="tool output",
            compact_schema="- needs_more_tool_calls",
        ),
    )
    assert "tool output" in dto.content
    assert dto.metadata.get("intent") == "workspace_context_validation"


def test_missing_registered_intent_raises(tmp_path: Path) -> None:
    reg_file = tmp_path / "prompt_registry.toml"
    reg_file.write_text("[intents]\n", encoding="utf-8")
    reg = FilePromptRegistry(assets_dir=tmp_path, registry_path=reg_file)
    with pytest.raises(KeyError):
        reg.resolve_prompt(PromptIntent.SUPERVISOR_ROUTING, PromptContext())
