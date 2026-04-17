#!/usr/bin/env sh

set -eu

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but was not found in PATH." >&2
  exit 1
fi

if [ -f "uv.lock" ]; then
  uv sync --frozen --extra dev
else
  uv sync --extra dev
fi

echo "Dependencies are synced."
