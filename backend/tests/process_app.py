"""Test-only app factory. Never packaged into the production image."""

import asyncio
import os
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import make_url
from test_policy_chat import PolicyModel

from app.config import Settings
from app.db import Database
from app.main import create_app as hotel_app


class ReceiptModel(PolicyModel):
    async def generate_content_async(self, request, stream=False):
        last = request.contents[-1]
        if not any(p.function_response for p in last.parts):
            marker = UUID(next(p.text for p in last.parts if p.text).split()[-1])
            db = Database(os.environ["TEST_DATABASE_URL"])
            try:
                async with db.transaction() as c:
                    await c.execute(
                        text(
                            "INSERT INTO test_model_receipts(id,calls) VALUES(:id,1) ON CONFLICT(id) DO UPDATE SET calls=test_model_receipts.calls+1"
                        ),
                        {"id": marker},
                    )
            finally:
                await db.close()
            await asyncio.sleep(float(os.environ.get("TEST_MODEL_DELAY", "0.2")))
        async for response in super().generate_content_async(request, stream):
            yield response


def create_app():
    url = make_url(os.environ["TEST_DATABASE_URL"])
    assert url.host in {"localhost", "127.0.0.1"} and url.database == "hotel_test"
    return hotel_app(
        Settings(
            _env_file=None,
            database_url=url.render_as_string(hide_password=False),
            google_cloud_project="",
            public_origins="http://test.hotel",
            app_env="demo",
            ip_hash_secret="test-only-not-a-production-secret-12345",
            property_turns_per_minute=10000,
            demo_ip_limit_override=10000,
        ),
        model=ReceiptModel(),
    )
