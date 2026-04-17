if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Error "uv is required but was not found in PATH."
  exit 1
}

if (Test-Path "uv.lock") {
  uv sync --frozen --extra dev
} else {
  uv sync --extra dev
}

if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}

uv run uvicorn app.main:app --reload
