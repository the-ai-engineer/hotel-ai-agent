#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m http.server "${PORT:-8773}" --bind 127.0.0.1 --directory frontend
