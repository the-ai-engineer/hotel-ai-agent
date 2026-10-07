import os
import uuid
from pathlib import Path

import asyncpg
import httpx
import pytest_asyncio

from app.db import migrate
from app.seed import import_policies
from app.settings import Settings

os.environ.setdefault(
    "DATABASE_URL", "postgresql://hotel:hotel@127.0.0.1:55439/hotel_policy"
)


@pytest_asyncio.fixture
async def pool():
    url = os.environ.get("TEST_DATABASE_URL", os.environ["DATABASE_URL"])
    schema = "test_" + uuid.uuid4().hex
    admin = await asyncpg.connect(url)
    await admin.execute(f"CREATE SCHEMA {schema}")
    pool = await asyncpg.create_pool(
        url, min_size=0, max_size=5, server_settings={"search_path": schema}
    )
    try:
        await migrate(pool)
        await import_policies(pool, Path(__file__).resolve().parents[2] / "hotel")
        yield pool
    finally:
        await pool.close()
        await admin.execute(f"DROP SCHEMA {schema} CASCADE")
        await admin.close()


@pytest_asyncio.fixture
async def client(pool, monkeypatch):
    from app import main

    async def connect(_):
        return pool

    monkeypatch.setattr(main, "connect", connect)
    app = main.create_app(Settings(database_url=os.environ["DATABASE_URL"]))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8773"
        ) as client:
            client.app = app
            yield client
