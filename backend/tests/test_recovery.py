import asyncio
from contextlib import aclosing
from contextvars import ContextVar
from uuid import uuid4

import pytest
from fastapi import HTTPException
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from google.genai.errors import ClientError
from sqlalchemy import text
from test_policy_chat import new

from app.agent import BoundedGemini, _model_deadline
from app.config import Settings
from app.limits import reserve
from app.streaming import with_heartbeats


async def test_api_limits_preserve_replay_and_do_not_admit_rejected_turn(client):
    client._transport.app.state.settings.property_turns_per_minute = 1
    conversation = await new(client)
    body = {"client_turn_id": str(uuid4()), "message": "breakfast"}
    assert (
        "event: done"
        in (await client.post(f"/api/conversations/{conversation}/turns", json=body)).text
    )
    assert (
        "event: done"
        in (await client.post(f"/api/conversations/{conversation}/turns", json=body)).text
    )
    rejected = await client.post(
        f"/api/conversations/{conversation}/turns", json={**body, "client_turn_id": str(uuid4())}
    )
    assert rejected.status_code == 429 and int(rejected.headers["retry-after"]) > 0
    assert len((await client.get(f"/api/conversations/{conversation}")).json()["turns"]) == 1
    conflict = await client.post(
        f"/api/conversations/{conversation}/turns", json={**body, "message": "different"}
    )
    assert conflict.status_code == 409 and conflict.json()["code"] == "idempotency_conflict"


async def test_counter_reservations_roll_back_together(db):
    settings = Settings(_env_file=None)
    async with db.transaction() as c:
        await reserve(c, settings, [("z", "key", 86400, 1)])
    with pytest.raises(HTTPException):
        async with db.transaction() as c:
            await reserve(c, settings, [("a", "key", 86400, 1), ("z", "key", 86400, 1)])
    async with db.transaction() as c:
        assert (
            await c.execute(text("SELECT count(*) FROM rate_buckets WHERE scope='a'"))
        ).scalar_one() == 0


async def test_history_cursor_handles_equal_timestamps(client):
    conversation = await new(client)
    db = client._transport.app.state.db
    async with db.transaction() as c:
        for _ in range(63):
            await c.execute(
                text(
                    "INSERT INTO turns(conversation_id,client_turn_id,message,state,deadline,created_at) VALUES(:id,:turn,'hello','interrupted',clock_timestamp(), '2026-01-01T00:00:00Z')"
                ),
                {"id": conversation, "turn": uuid4()},
            )
    first = (await client.get(f"/api/conversations/{conversation}")).json()
    second = (
        await client.get(
            f"/api/conversations/{conversation}", params={"before": first["next_cursor"]}
        )
    ).json()
    ids = [t["client_turn_id"] for t in second["turns"] + first["turns"]]
    assert len(first["turns"]) == 50 and len(ids) == len(set(ids)) == 63
    assert second["next_cursor"] is None
    assert (
        await client.get(f"/api/conversations/{conversation}", params={"before": "bad"})
    ).status_code == 400


async def test_chunked_oversized_body_is_rejected(client):
    conversation = await new(client)

    async def chunks():
        yield b'{"message":"'
        yield b"x" * 33000
        yield b'"}'

    response = await client.post(
        f"/api/conversations/{conversation}/turns",
        content=chunks(),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413


async def test_heartbeat_preserves_context_and_closes_silent_producer():
    context = ContextVar("test-context")
    closed = asyncio.Event()

    async def events():
        token = context.set("owned")
        try:
            yield 1
            await asyncio.sleep(0.02)
            assert context.get() == "owned"
            yield 2
            await asyncio.sleep(30)
        finally:
            context.reset(token)
            closed.set()

    async with aclosing(with_heartbeats(events(), seconds=0.005)) as stream:
        assert await anext(stream) == 1
        assert await anext(stream) is None
        while await anext(stream) != 2:
            pass
    assert closed.is_set()


@pytest.mark.parametrize(
    "emitted",
    [
        None,
        types.Part(text="visible"),
        types.Part(function_call=types.FunctionCall(name="search_policies", args={"query": "x"})),
    ],
)
async def test_model_retries_only_before_visible_output(monkeypatch, emitted):
    calls = 0

    async def upstream(self, request, stream=False):
        nonlocal calls
        calls += 1
        if calls == 1:
            if emitted:
                yield LlmResponse(content=types.Content(role="model", parts=[emitted]))
            raise ClientError(429, {"error": {"message": "limited"}})
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="ok")]))

    monkeypatch.setattr(Gemini, "generate_content_async", upstream)
    monkeypatch.setattr("app.agent.random.uniform", lambda *args: 0)
    model = BoundedGemini(model="test")
    if emitted:
        with pytest.raises(ClientError):
            async for _ in model.generate_content_async(LlmRequest()):
                pass
        assert calls == 1
    else:
        assert len([e async for e in model.generate_content_async(LlmRequest())]) == 1
        assert calls == 2


async def test_retry_respects_remaining_deadline(monkeypatch):
    calls = 0

    async def upstream(self, request, stream=False):
        nonlocal calls
        calls += 1
        raise ClientError(503, {"error": {"message": "unavailable"}})
        yield

    monkeypatch.setattr(Gemini, "generate_content_async", upstream)
    token = _model_deadline.set(asyncio.get_running_loop().time())
    try:
        with pytest.raises(ClientError):
            async for _ in BoundedGemini(model="test").generate_content_async(LlmRequest()):
                pass
        assert calls == 1
    finally:
        _model_deadline.reset(token)


def test_private_demo_override_is_rejected_in_production():
    with pytest.raises(ValueError, match="private demo"):
        Settings(
            _env_file=None,
            app_env="production",
            ip_hash_secret="x" * 32,
            property_turns_per_minute=100,
            demo_ip_limit_override=100,
        )
