"""Shared helpers: sync requirements.txt from pyproject.toml and venv install."""

from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path


def project_root_from_env(*, fallback: Path | None = None) -> Path:
    env = os.environ.get("CURSOR_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    if fallback is not None:
        return fallback.resolve()
    return Path.cwd().resolve()


def find_venv_python(root: Path) -> Path | None:
    if sys.platform == "win32":
        candidates = [
            root / ".venv" / "Scripts" / "python.exe",
            root / "venv" / "Scripts" / "python.exe",
        ]
    else:
        candidates = [root / ".venv" / "bin" / "python", root / "venv" / "bin" / "python"]
    for p in candidates:
        if p.is_file():
            return p
    return None


def write_requirements_from_pyproject(root: Path) -> None:
    pyproject = root / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    deps = list(data.get("project", {}).get("dependencies") or [])
    out = root / "requirements.txt"
    lines = [
        "# Synced from pyproject.toml [project.dependencies]. Regenerate:",
        "#   python hooks/generate_requirements.py",
        "",
    ]
    lines.extend(deps)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def pip_install_editable(root: Path, *, python_exe: Path) -> int:
    return subprocess.run(
        [str(python_exe), "-m", "pip", "install", "-e", str(root)],
        cwd=str(root),
        check=False,
    ).returncode


def ensure_git_hooks_configured(root: Path) -> None:
    """Configure repo-local git hooks path so hooks run in any editor."""
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or result.stdout.strip().lower() != "true":
        return

    subprocess.run(
        ["git", "config", "--local", "core.hooksPath", "hooks"],
        cwd=str(root),
        check=False,
        capture_output=True,
        text=True,
    )
