"""Regenerate requirements.txt from pyproject.toml [project.dependencies].

Run:  python hooks/generate_requirements.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from hooks.shared import project_root_from_env, write_requirements_from_pyproject  # noqa: E402


def main() -> None:
    root = project_root_from_env(fallback=_REPO_ROOT)
    write_requirements_from_pyproject(root)
    print(f"Wrote {root / 'requirements.txt'}")


if __name__ == "__main__":
    main()
