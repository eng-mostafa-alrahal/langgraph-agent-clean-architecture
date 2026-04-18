"""Tests for MCP filesystem path normalization (repo-root vs sandbox)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.infrastructure.mcp_gateways.path_interceptor import normalize_path_string


@pytest.fixture
def roots() -> tuple[Path, Path]:
    """Synthetic repo layout matching typical ``mcp_workspace`` nesting."""
    project = Path(r"C:\repo\example")
    sandbox = project / "mcp_workspace"
    return sandbox, project


def test_normalize_repo_root_filename_to_basename(roots: tuple[Path, Path]) -> None:
    sandbox_root, project_root = roots
    bad = str(project_root / "example.txt")
    expected = str((sandbox_root / "example.txt").resolve())
    assert normalize_path_string(bad, sandbox_root, project_root) == expected


def test_normalize_already_inside_sandbox_relative(roots: tuple[Path, Path]) -> None:
    sandbox_root, project_root = roots
    inside = str(sandbox_root / "notes" / "a.txt")
    expected = str((sandbox_root / "notes" / "a.txt").resolve())
    assert normalize_path_string(inside, sandbox_root, project_root) == expected


def test_normalize_relative_unchanged(roots: tuple[Path, Path]) -> None:
    sandbox_root, project_root = roots
    expected = str((sandbox_root / "example.txt").resolve())
    assert normalize_path_string("example.txt", sandbox_root, project_root) == expected
