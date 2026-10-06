import os

import httpx
import pytest
from sqlalchemy import text

from app.cli import seed
from app.config import Settings
from app.db import Database


@pytest.fixture
async def db():
    settings = Settings(
        _env_file=None,
        google_cloud_project="",
        database_url=os.environ["TEST_DATABASE_URL"],
    )
    from sqlalchemy.engine import make_url

    url = make_url(settings.database_url)
    assert url.host in {"127.0.0.1", "localhost"} and url.database == "hotel_test", (
        "Tests require isolated local hotel_test database"
    )
    cleanup = Database(settings.database_url)
    async with cleanup.transaction() as c:
        await c.execute(
            text(
                "TRUNCATE guest_sessions,policy_sections,policy_versions,villas,demo_inventory,rate_buckets CASCADE"
            )
        )
    await cleanup.close()
    await seed(settings)
    database = Database(settings.database_url)
    await database.ready()
    yield database
    await database.close()


@pytest.fixture
async def client(db):
    from test_policy_chat import PolicyModel

    from app.main import create_app

    app = create_app(
        Settings(
            _env_file=None,
            google_cloud_project="",
            database_url=os.environ["TEST_DATABASE_URL"],
        ),
        db=db,
        model=PolicyModel(),
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1:8773",
            headers={"Origin": "http://127.0.0.1:8773"},
        ) as client:
            yield client
