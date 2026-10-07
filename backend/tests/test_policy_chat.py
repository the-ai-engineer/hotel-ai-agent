import asyncio
import os
from uuid import uuid4

import httpx
import pytest
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import PrivateAttr
from sqlalchemy import text

from app import hotel, turns
from app.agent import Concierge
from app.cli import seed
from app.config import Settings
from app.db import Database
from app.main import create_app
from app.schemas import TurnInput


class PolicyModel(BaseLlm):
    model: str = "test-policy"
    calls: int = 0
    _prompts: list = PrivateAttr(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        self.calls += 1
        self._prompts.append([p.text for c in llm_request.contents for p in c.parts if p.text])
        last = llm_request.contents[-1]
        responses = [p.function_response for p in last.parts if p.function_response]
        if responses:
            passages = responses[0].response["passages"]
            answer = passages[0]["passage"] if passages else "Please contact the hotel."
            yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=answer)]))
        else:
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="search_policies", args={"query": "breakfast"}
                            )
                        )
                    ],
                )
            )


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
        await c.execute(text("TRUNCATE guest_sessions,policy_sections,policy_versions CASCADE"))
    await cleanup.close()
    await seed(settings)
    database = Database(settings.database_url)
    await database.ready()
    yield database
    await database.close()


@pytest.fixture
async def client(db):
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


async def new(client):
    assert (await client.post("/api/session", json={})).status_code == 200
    return (await client.post("/api/conversations", json={})).json()["id"]


async def test_real_adk_tool_loop_history_sources_and_replay(client):
    conversation = await new(client)
    id = str(uuid4())
    body = {"client_turn_id": id, "message": "When is breakfast?"}
    result = await client.post(f"/api/conversations/{conversation}/turns", json=body)
    assert "event: done" in result.text and "07:00" in result.text
    assert "/policies/breakfast?version=1" in result.text
    replay = await client.post(f"/api/conversations/{conversation}/turns", json=body)
    assert "event: done" in replay.text
    history = (await client.get(f"/api/conversations/{conversation}")).json()["turns"]
    assert len(history) == 1 and history[0]["state"] == "completed"
    followup = await client.post(
        f"/api/conversations/{conversation}/turns",
        json={"client_turn_id": str(uuid4()), "message": "Is it included?"},
    )
    assert "event: done" in followup.text
    assert (await client.get("/policies/breakfast")).status_code == 200
    assert (await client.get("/policies/breakfast?version=1")).status_code == 200
    assert (await client.get("/api/unknown")).status_code == 404


async def test_cross_guest_reads_and_writes_are_hidden(client):
    conversation = await new(client)
    client.cookies.clear()
    await new(client)
    assert (await client.get(f"/api/conversations/{conversation}")).status_code == 404
    assert (
        await client.post(
            f"/api/conversations/{conversation}/turns",
            json={"client_turn_id": str(uuid4()), "message": "breakfast"},
        )
    ).status_code == 404
    assert (
        await client.get(f"/api/conversations/{conversation}/turns/{uuid4()}")
    ).status_code == 404


async def test_boundary_rejects_origin_and_oversized_message(client):
    conversation = await new(client)
    assert (
        await client.post("/api/session", json={}, headers={"Origin": "https://evil.example"})
    ).status_code == 403
    assert (
        await client.post(
            f"/api/conversations/{conversation}/turns",
            json={"client_turn_id": str(uuid4()), "message": "x" * 2001},
        )
    ).status_code == 400


async def test_parallel_admission_and_deadline(db):
    owner = uuid4()
    async with db.transaction() as c:
        await c.execute(
            text("INSERT INTO guest_sessions(id,token_hash) VALUES(:id,:hash)"),
            {"id": owner, "hash": str(owner)},
        )
    conversation = await turns.create_conversation(db, owner)
    first = TurnInput(client_turn_id=uuid4(), message="breakfast")

    async def admit():
        try:
            return await turns.admit(db, conversation, owner, first, 90)
        except Exception as e:
            return e

    results = await asyncio.gather(admit(), admit())
    assert sum(isinstance(r, tuple) for r in results) == 1
    async with db.transaction() as c:
        await c.execute(
            text(
                "UPDATE turns SET deadline=clock_timestamp()-interval '1 second' WHERE conversation_id=:id"
            ),
            {"id": conversation},
        )
    assert not await turns.finish(
        db, conversation, first.client_turn_id, "completed", {"answer": "late", "sources": []}
    )
    assert (await turns.status(db, conversation, owner, first.client_turn_id))[
        "state"
    ] == "interrupted"


async def test_unpublished_policy_is_never_retrieved_or_served(db):
    id = uuid4()
    slug = "private-" + id.hex
    async with db.transaction() as c:
        await c.execute(
            text(
                "INSERT INTO policy_versions(id,slug,title,version) VALUES(:id,:slug,'Private',1)"
            ),
            {"id": id, "slug": slug},
        )
        await c.execute(
            text(
                "INSERT INTO policy_sections(id,version_id,position,body) VALUES(:id,:v,1,'breakfast private secret')"
            ),
            {"id": uuid4(), "v": id},
        )
    assert await hotel.policy_page(db, slug, 1) == []
    assert all(
        p["source"]["title"] != "Private" for p in await hotel.search_policies(db, "breakfast")
    )


async def test_missing_model_fails_without_inventing_answer(db):
    concierge = Concierge(
        Settings(
            _env_file=None,
            google_cloud_project="",
            database_url=os.environ["TEST_DATABASE_URL"],
        ),
        db,
    )
    with pytest.raises(RuntimeError, match="not configured"):
        async for _ in concierge.run(uuid4(), "breakfast", []):
            pass


async def test_request_local_adk_history_does_not_leak(db):
    model = PolicyModel()
    concierge = Concierge(
        Settings(
            _env_file=None,
            google_cloud_project="",
            database_url=os.environ["TEST_DATABASE_URL"],
        ),
        db,
        model,
    )

    async def run(marker):
        history = [{"message": marker, "result": {"answer": "Earlier answer"}}]
        return [event async for event in concierge.run(uuid4(), "breakfast", history)]

    a, b = await asyncio.gather(run("guest-a-private"), run("guest-b-private"))
    assert a[-1]["event"] == b[-1]["event"] == "answer"
    assert any("guest-a-private" in prompt for prompt in model._prompts)
    assert any("guest-b-private" in prompt for prompt in model._prompts)
    assert not any(
        "guest-a-private" in prompt and "guest-b-private" in prompt for prompt in model._prompts
    )


async def test_pinned_adk_uses_explicit_vertex_client(db, monkeypatch):
    from google.auth.credentials import AnonymousCredentials

    import app.agent as adapter

    original = adapter.Client
    captured = {}

    def client(**kwargs):
        captured.update(kwargs)
        return original(**kwargs, credentials=AnonymousCredentials())

    monkeypatch.setattr(adapter, "Client", client)
    concierge = Concierge(
        Settings(_env_file=None, google_cloud_project="test-explicit-project"), db
    )
    assert concierge.model.api_client is concierge.client
    assert captured["project"] == "test-explicit-project"
    assert captured["vertexai"] is True
    assert captured["http_options"].retry_options.attempts == 1
    await concierge.close()


async def test_disconnect_closes_run_and_marks_interrupted(client):
    import json

    app = client._transport.app
    conversation = await new(client)
    closed = asyncio.Event()
    started = asyncio.Event()

    class SlowConcierge:
        async def run(self, *args):
            try:
                yield {"event": "text_delta", "data": {"text": "Starting"}}
                await asyncio.sleep(30)
            finally:
                closed.set()

    original = app.state.concierge
    app.state.concierge = SlowConcierge()
    id = str(uuid4())
    body = json.dumps({"client_turn_id": id, "message": "breakfast"}).encode()
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await started.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.body" and b"event: text_delta" in message.get(
            "body", b""
        ):
            started.set()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": f"/api/conversations/{conversation}/turns",
        "raw_path": b"/api",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"127.0.0.1:8773"),
            (b"origin", b"http://127.0.0.1:8773"),
            (b"content-type", b"application/json"),
            (b"cookie", ("; ".join(f"{k}={v}" for k, v in client.cookies.items())).encode()),
        ],
        "client": ("127.0.0.1", 1234),
        "server": ("127.0.0.1", 8773),
    }
    try:
        await asyncio.wait_for(app(scope, receive, send), 3)
        assert closed.is_set()
        status = (await client.get(f"/api/conversations/{conversation}/turns/{id}")).json()
        assert status["state"] == "interrupted"
    finally:
        app.state.concierge = original
