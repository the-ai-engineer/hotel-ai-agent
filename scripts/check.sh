#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv run --project backend ruff check backend/app backend/tests backend/migrations
uv run --project backend ruff format --check backend/app backend/tests backend/migrations
export TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql+asyncpg://hotel:hotel@127.0.0.1:55439/hotel_test}"
uv run --project backend python -c 'import os; from sqlalchemy.engine import make_url; u=make_url(os.environ["TEST_DATABASE_URL"]); assert u.host in {"127.0.0.1","localhost"} and u.database == "hotel_test", "Tests require local hotel_test"'
DATABASE_URL="$TEST_DATABASE_URL" uv run --project backend --directory backend alembic upgrade head
(cd backend && uv run pytest)
node --test frontend/tests/*.test.js
python3 scripts/verify_website.py
