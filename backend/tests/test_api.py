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


async def test_disconnect_before_stream_starts_releases_admission(client, pool):
    import asyncio
    import json

    await start(client)
    called = False

    async def model(pool, settings, history, question):
        nonlocal called
        called = True
        yield {"type": "result", "answer": "Not reached", "sources": []}

    client.app.state.answer = model
    turn_id = uuid.uuid4()
    body = json.dumps({"turn_id": str(turn_id), "message": "Breakfast?"}).encode()
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            # Disconnect cancels the response before it enters the body iterator.
            await asyncio.Event().wait()

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
    assert not called
    async with pool.acquire() as conn:
        assert (
            await conn.fetchval("SELECT status FROM turns WHERE id=$1", turn_id)
            == "interrupted"
        )
        assert await conn.fetchval("SELECT active_turn FROM guest_sessions") is None


async def test_new_conversation_clears_context_and_survives_refresh_without_deletion(
    client, pool
):
    await start(client)
    calls = []

    async def success(pool, settings, history, question):
        calls.append(history)
        yield {"type": "result", "answer": "Saved reply", "sources": []}

    client.app.state.answer = success
    await client.post(
        "/api/chat",
        headers=ORIGIN,
        json={"turn_id": str(uuid.uuid4()), "message": "First conversation"},
    )
    cookie = client.cookies["hotel_session"]
    assert (await client.get("/api/history")).json()["turns"]
    assert (await client.post("/api/conversation", headers=ORIGIN)).status_code == 200
    assert client.cookies["hotel_session"] == cookie
    assert (await client.get("/api/history")).json()["turns"] == []
    async with pool.acquire() as conn:
        assert await conn.fetchval("SELECT count(*) FROM turns") == 1
    await client.post(
        "/api/chat",
        headers=ORIGIN,
        json={"turn_id": str(uuid.uuid4()), "message": "Fresh conversation"},
    )
    assert calls == [[], []]
    assert len((await client.get("/api/history")).json()["turns"]) == 1


async def test_new_conversation_respects_origin_owner_and_active_turn(client, pool):
    assert (await client.post("/api/conversation", headers=ORIGIN)).status_code == 401
    await start(client)
    assert (
        await client.post(
            "/api/conversation", headers={"Origin": "https://evil.example"}
        )
    ).status_code == 403
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE guest_sessions SET busy_until=now()+interval '1 minute'"
        )
    assert (await client.post("/api/conversation", headers=ORIGIN)).status_code == 409


async def test_availability_result_is_saved_in_history(client, pool):
    from app.inventory import check_availability

    await start(client)
    availability = await check_availability(pool, "2026-11-01", "2026-11-04", 4)

    async def success(pool, settings, history, question):
        yield {
            "type": "result",
            "answer": "Garden Villa is available.",
            "sources": [],
            "availability": availability,
        }

    client.app.state.answer = success
    response = await client.post(
        "/api/chat",
        headers=ORIGIN,
        json={"turn_id": str(uuid.uuid4()), "message": "Which villa for four?"},
    )
    assert "event: done" in response.text
    saved = (await client.get("/api/history")).json()["turns"][0]["availability"]
    assert saved == availability
    assert [villa["id"] for villa in saved["cards"]] == ["garden-villa"]
