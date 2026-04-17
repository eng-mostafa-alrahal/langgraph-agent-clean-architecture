#!/usr/bin/env python3
"""Cursor beforeShellExecution: sync requirements.txt when running `git commit`."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from custom_hooks.sync_requirements import (  # noqa: E402
    project_root_from_env,
    write_requirements_from_pyproject,
)

# Matcher also restricts which commands run this hook; keep in sync with hooks.json.
_COMMIT = re.compile(r"git\s+commit(?:\s|$)")


def main() -> None:
    allow = {"permission": "allow"}
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps(allow), flush=True)
        return

    command = payload.get("command") or ""
    if not _COMMIT.search(command):
        print(json.dumps(allow), flush=True)
        return

    root = project_root_from_env(fallback=_ROOT)
    try:
        write_requirements_from_pyproject(root)
    except OSError:
        pass

    print(json.dumps(allow), flush=True)


if __name__ == "__main__":
    main()
