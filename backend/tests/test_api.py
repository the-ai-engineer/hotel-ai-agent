import uuid

import httpx

ORIGIN = {"Origin": "http://127.0.0.1:8773"}


async def start(client):
    response = await client.post("/api/session", headers=ORIGIN)
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]


async def test_policy_sources_unknown_and_unpublished(client, pool):
    response = await client.get("/api/sources/dining-policy/2")
    assert response.status_code == 200
    assert "10:30" in response.text
    assert (await client.get("/api/sources/private-staff/1")).status_code == 404
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE documents SET published=false WHERE id='dining-policy'"
        )
    assert (await client.get("/api/sources/dining-policy/2")).status_code == 404


async def test_guest_origin_ownership_expiry(client, pool):
    assert (await client.get("/api/history")).status_code == 401
    assert (
        await client.post("/api/session", headers={"Origin": "https://evil.example"})
    ).status_code == 403
    await start(client)

    async def fake(pool, settings, history, question):
        assert history == []
        yield {"type": "result", "answer": "Saved test answer", "sources": []}

    client.app.state.answer = fake
    response = await client.post(
        "/api/chat",
        headers=ORIGIN,
        json={"turn_id": str(uuid.uuid4()), "message": "Breakfast?"},
    )
    assert "event: done" in response.text
    assert (await client.get("/api/history")).json()["turns"][0][
        "answer"
    ] == "Saved test answer"
    async with httpx.AsyncClient(
        transport=client._transport, base_url="http://127.0.0.1:8773"
    ) as other:
        await start(other)
        assert (await other.get("/api/history")).json()["turns"] == []
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE guest_sessions SET expires_at=now()-interval '1 second'"
        )
    assert (await client.get("/api/history")).status_code == 401


async def test_failed_stream_does_not_save_partial_and_releases_lock(client):
    await start(client)

    async def fail(pool, settings, history, question):
        yield {"type": "text", "text": "Partial"}
        raise RuntimeError("private failure detail")

    client.app.state.answer = fail
    response = await client.post(
        "/api/chat",
        headers=ORIGIN,
        json={"turn_id": str(uuid.uuid4()), "message": "Breakfast?"},
    )
    assert "event: text" in response.text and "event: error" in response.text
    assert (
        "event: done" not in response.text
        and "private failure detail" not in response.text
    )
    assert (await client.get("/api/history")).json()["turns"] == []

    async def success(pool, settings, history, question):
        yield {"type": "result", "answer": "Retry works", "sources": []}

    client.app.state.answer = success
    assert (
        "event: done"
        in (
            await client.post(
                "/api/chat",
                headers=ORIGIN,
                json={"turn_id": str(uuid.uuid4()), "message": "Breakfast?"},
            )
        ).text
    )


async def test_duplicate_and_bad_input_do_not_invoke_model(client):
    await start(client)
    calls = []

    async def success(pool, settings, history, question):
        calls.append(question)
        yield {"type": "result", "answer": "Test answer", "sources": []}

    client.app.state.answer = success
    data = {"turn_id": str(uuid.uuid4()), "message": "Breakfast?"}
    assert (
        await client.post("/api/chat", headers=ORIGIN, json=data)
    ).status_code == 200
    assert (
        await client.post("/api/chat", headers=ORIGIN, json=data)
    ).status_code == 409
    assert (
        await client.post("/api/chat", headers=ORIGIN, json={**data, "message": " "})
    ).status_code == 422
    assert (
        await client.post(
            "/api/chat", headers=ORIGIN, json={**data, "message": "x" * 2001}
        )
    ).status_code == 422
    assert calls == ["Breakfast?"]


async def test_disconnect_cleans_up_inside_cancelled_asgi_scope(client, pool):
    import asyncio
    import json

    await start(client)
    model_started = asyncio.Event()

    async def waiting(pool, settings, history, question):
        model_started.set()
        await asyncio.Event().wait()
        yield {"type": "result", "answer": "Never reached", "sources": []}

    client.app.state.answer = waiting
    turn_id = uuid.uuid4()
    body = json.dumps({"turn_id": str(turn_id), "message": "Breakfast?"}).encode()
    sent_request = False

    async def receive():
        nonlocal sent_request
        if not sent_request:
            sent_request = True
            return {"type": "http.request", "body": body, "more_body": False}
        await model_started.wait()
        return {"type": "http.disconnect"}

    sent = []

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/chat",
        "raw_path": b"/api/chat",
        "query_string": b"",
        "root_path": "",
        "server": ("127.0.0.1", 8773),
        "client": ("127.0.0.1", 10000),
        "headers": [
            (b"origin", ORIGIN["Origin"].encode()),
            (b"content-type", b"application/json"),
            (b"cookie", f"hotel_session={client.cookies['hotel_session']}".encode()),
        ],
    }
    await asyncio.wait_for(client.app(scope, receive, send), 5)
    async with pool.acquire() as conn:
        assert (
            await conn.fetchval("SELECT status FROM turns WHERE id=$1", turn_id)
            == "interrupted"
        )
        assert await conn.fetchval("SELECT active_turn FROM guest_sessions") is None

    async def success(pool, settings, history, question):
        yield {"type": "result", "answer": "Immediate retry", "sources": []}

    client.app.state.answer = success
    response = await client.post(
        "/api/chat",
        headers=ORIGIN,
        json={"turn_id": str(uuid.uuid4()), "message": "Retry"},
    )
    assert "event: done" in response.text
