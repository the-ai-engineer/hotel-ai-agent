from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


class Database:
    def __init__(self, url: str):
        self.engine = create_async_engine(
            url,
            pool_size=5,
            max_overflow=0,
            pool_timeout=3,
            pool_pre_ping=True,
            connect_args={"server_settings": {"statement_timeout": "5000"}},
        )

    @asynccontextmanager
    async def transaction(self):
        async with self.engine.begin() as connection:
            yield connection

    async def ready(self):
        async with self.transaction() as connection:
            row = (
                await connection.execute(
                    text("SELECT schema_version, min_app_schema FROM schema_contract WHERE id=1")
                )
            ).one()
            if not row.schema_version >= 2 >= row.min_app_schema:
                raise RuntimeError("Incompatible database schema")

    async def close(self):
        await self.engine.dispose()
