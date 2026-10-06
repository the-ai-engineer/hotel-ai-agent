import asyncio
import hashlib
from pathlib import Path

import asyncpg

from app.settings import Settings


async def connect(settings):
    pool = await asyncpg.create_pool(settings.database_url, min_size=0, max_size=5)
    return pool


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


async def migrate(pool):
    # Explicit release command, never run during web startup.
    async with pool.acquire(timeout=3) as conn, conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(431297)")
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY)"
        )
        for path in sorted((Path(__file__).parents[1] / "migrations").glob("*.sql")):
            exists = await conn.fetchval(
                "SELECT 1 FROM schema_migrations WHERE name=$1", path.name
            )
            if not exists:
                await conn.execute(path.read_text())
                await conn.execute(
                    "INSERT INTO schema_migrations VALUES ($1)", path.name
                )


async def command():
    import sys

    pool = await connect(Settings())
    try:
        if sys.argv[1:] == ["migrate"]:
            await migrate(pool)
            print("Migrations applied.")
        elif sys.argv[1:] == ["seed"]:
            from app.seed import import_policies

            await import_policies(pool, Path(__file__).resolve().parents[2] / "hotel")
            print("Hotel policies imported.")
        else:
            raise SystemExit("Usage: python -m app.db migrate|seed")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(command())
