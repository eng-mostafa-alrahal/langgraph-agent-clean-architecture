#!/usr/bin/env python3
"""Cursor sessionStart: pip install -e . in project .venv (installs missing deps)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from hooks.shared import (  # noqa: E402
    ensure_git_hooks_configured,
    find_venv_python,
    pip_install_editable,
    project_root_from_env,
)


def main() -> None:
    try:
        sys.stdin.read()
    except Exception:
        pass

    root = project_root_from_env(fallback=_ROOT)
    ensure_git_hooks_configured(root)
    py = find_venv_python(root)
    if py is None:
        print(json.dumps({}), flush=True)
        return

    pip_install_editable(root, python_exe=py)
    print(json.dumps({}), flush=True)


if __name__ == "__main__":
    main()
