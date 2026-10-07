#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run --project backend uvicorn app.main:create_app --factory --app-dir backend --host 127.0.0.1 --port "${PORT:-8773}"
