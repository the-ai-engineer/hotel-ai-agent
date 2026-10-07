"""Credential-free HTTP worker used only by the multiprocess acceptance tests."""

import asyncio
import json
import os
from contextlib import asynccontextmanager

import asyncpg
import uvicorn

from app import main
from app.settings import Settings


async def connect(settings):
    return await asyncpg.create_pool(
        settings.database_url,
        min_size=0,
        max_size=5,
        server_settings={"search_path": os.environ["TEST_SCHEMA"]},
    )


async def deterministic_answer(pool, settings, history, question, guest=None):
    yield {"type": "text", "text": "Provisional"}
    await asyncio.sleep(20 if question == "wait" else 1.5)
    if question == "fail":
        raise RuntimeError("private test failure")
    yield {
        "type": "result",
        "answer": json.dumps({"question": question, "history": history}),
        "sources": [],
    }


main.connect = connect
app = main.create_app(Settings())
original = app.router.lifespan_context


@asynccontextmanager
async def lifespan(app):
    async with original(app):
        app.state.answer = deterministic_answer
        yield


app.router.lifespan_context = lifespan
if __name__ == "__main__":
    uvicorn.run(
        app, host="127.0.0.1", port=int(os.environ["TEST_PORT"]), log_level="warning"
    )
