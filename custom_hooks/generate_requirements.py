"""Hook script: regenerate requirements.txt from pyproject.toml.

Run with:  python custom_hooks/generate_requirements.py
"""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        stdout=open("requirements.txt", "w"),
        check=True,
    )
    print("requirements.txt regenerated.")


if __name__ == "__main__":
    main()
