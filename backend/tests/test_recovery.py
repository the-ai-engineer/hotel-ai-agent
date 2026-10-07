import asyncio
import json
import os
import socket
import subprocess
import sys
import uuid
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from test_api import ORIGIN, start

from app.db import token_hash
from app.turns import ModelAdmission, budget


async def result_model(pool, settings, history, question, guest=None):
    yield {"type": "result", "answer": "Saved", "sources": []}


async def test_replay_status_stop_and_foreign_ownership(client):
    await start(client)
    client.app.state.answer = result_model
    data = {"turn_id": str(uuid.uuid4()), "message": "Breakfast?"}
    await client.post("/api/chat", headers=ORIGIN, json=data)
    url = f"/api/turns/{data['turn_id']}"
    assert (await client.get(url)).json()["result"]["answer"] == "Saved"
    assert (await client.post(url + "/stop", headers=ORIGIN)).json()[
        "status"
    ] == "completed"
    assert (
        await client.post(url + "/stop", headers={"Origin": "https://evil.example"})
    ).status_code == 403
    async with httpx.AsyncClient(
        transport=client._transport, base_url=str(client.base_url)
    ) as other:
        await start(other)
        assert (await other.get(url)).status_code == 404
        assert (await other.post(url + "/stop", headers=ORIGIN)).status_code == 404
        assert (
            await other.post("/api/chat", headers=ORIGIN, json=data)
        ).status_code == 404
    await client.post("/api/conversation", headers=ORIGIN)
    assert (await client.get(url)).status_code == 404


async def test_crash_expiry_and_failed_retry_do_not_restart_uuid(client, pool):
    await start(client)
    key = token_hash(client.cookies["hotel_session"])
    turn_id = uuid.uuid4()
    async with pool.acquire() as conn:
        conversation = await conn.fetchval(
            "SELECT conversation_id FROM guest_sessions WHERE token_hash=$1", key
        )
        await conn.execute(
            "INSERT INTO turns(id,session_hash,question,status,conversation_id,deadline_at) VALUES ($1,$2,'crashed','running',$3,now()-interval '1 second')",
            turn_id,
            key,
            conversation,
        )
        await conn.execute(
            "UPDATE guest_sessions SET active_turn=$2,busy_until=now()-interval '1 second' WHERE token_hash=$1",
            key,
            turn_id,
        )
    state = (await client.get(f"/api/turns/{turn_id}")).json()
    assert state["status"] == "interrupted"
    calls = []

    async def counted(*args, **kwargs):
        calls.append(1)
        yield {"type": "result", "answer": "Fresh", "sources": []}

    client.app.state.answer = counted
    assert (
        await client.post(
            "/api/chat",
            headers=ORIGIN,
            json={"turn_id": str(turn_id), "message": "retry"},
        )
    ).json()["status"] == "interrupted"
    assert not calls
    assert (
        "event: done"
        in (
            await client.post(
                "/api/chat",
                headers=ORIGIN,
                json={"turn_id": str(uuid.uuid4()), "message": "fresh"},
            )
        ).text
    )
    assert calls == [1]


async def test_late_result_and_failed_commit_never_complete(client, pool):
    await start(client)
    turn_id = uuid.uuid4()

    async def late(*args, **kwargs):
        # A concurrent Stop wins before this producer returns its final output.
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE turns SET status='interrupted' WHERE id=$1", turn_id
            )
        yield {"type": "result", "answer": "Late", "sources": []}

    client.app.state.answer = late
    response = await client.post(
        "/api/chat", headers=ORIGIN, json={"turn_id": str(turn_id), "message": "late"}
    )
    assert "event: done" not in response.text
    assert (await client.get(f"/api/turns/{turn_id}")).json()["status"] == "interrupted"
    async with pool.acquire() as conn:
        await conn.execute(
            "CREATE FUNCTION reject_final() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.status='completed' THEN RAISE EXCEPTION 'injected commit failure'; END IF; RETURN NEW; END $$"
        )
        await conn.execute(
            "CREATE TRIGGER reject_final BEFORE UPDATE ON turns FOR EACH ROW EXECUTE FUNCTION reject_final()"
        )
    client.app.state.answer = result_model
    failed = uuid.uuid4()
    response = await client.post(
        "/api/chat",
        headers=ORIGIN,
        json={"turn_id": str(failed), "message": "commit failure"},
    )
    assert "event: done" not in response.text and "event: result" not in response.text
    assert (await client.get(f"/api/turns/{failed}")).json()["status"] == "failed"
    assert (await client.get("/api/history")).json()["turns"] == []
    assert client.app.state.model_admission.active == 0


async def test_property_daily_budget_uses_local_midnight_and_atomic_rollback(pool):
    from fastapi import HTTPException

    async with pool.acquire() as conn, conn.transaction():
        await budget(conn, [("day", 1, True)])
        assert await conn.fetchval(
            "SELECT bucket=(date_trunc('day',now() AT TIME ZONE 'Asia/Makassar') AT TIME ZONE 'Asia/Makassar') FROM rate_counters WHERE scope='day'"
        )
    with pytest.raises(HTTPException):
        async with pool.acquire() as conn, conn.transaction():
            await budget(conn, [("aaa", 10, False), ("day", 1, True)])
    async with pool.acquire() as conn:
        assert (
            await conn.fetchval("SELECT count(*) FROM rate_counters WHERE scope='aaa'")
            == 0
        )
        assert (
            await conn.fetchval("SELECT used FROM rate_counters WHERE scope='day'") == 1
        )


@pytest_asyncio.fixture
async def workers(pool, request):
    async with pool.acquire() as conn:
        schema = await conn.fetchval("SELECT current_schema()")
    processes = []
    clients = []
    try:
        for _ in range(2):
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            env = {
                **os.environ,
                "TEST_SCHEMA": schema,
                "PYTHONPATH": str(Path(__file__).parents[1]),
                "TEST_PORT": str(port),
                "DATABASE_URL": os.environ.get(
                    "TEST_DATABASE_URL", os.environ["DATABASE_URL"]
                ),
                "ACTIVE_AGENT_LIMIT": "12",
                "SESSIONS_PER_IP_MINUTE": "100",
                "IP_TURNS_PER_MINUTE": "100",
                "PROPERTY_TURNS_PER_MINUTE": "100",
            }
            env.update(getattr(request, "param", {}))
            process = subprocess.Popen(
                [sys.executable, "tests/recovery_worker.py"],
                env=env,
                cwd=Path(__file__).parents[1],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            processes.append(process)
            client = httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=10)
            client.worker_process = process
            clients.append(client)
            for _ in range(100):
                assert process.poll() is None, "Test worker exited"
                try:
                    if (await client.get("/api/health")).status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                await asyncio.sleep(0.05)
            else:
                pytest.fail("Test worker did not start")
        yield clients
    finally:
        for client in clients:
            await client.aclose()
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


async def test_twenty_conversations_across_two_processes_are_isolated(workers, pool):
    async def guest(index):
        async with httpx.AsyncClient(
            base_url=str(workers[index % 2].base_url), timeout=10
        ) as client:
            await start(client)
            data = {"turn_id": str(uuid.uuid4()), "message": f"guest-{index}"}
            response = await client.post("/api/chat", headers=ORIGIN, json=data)
            assert "event: done" in response.text
            # Reach the other process with the same cookie, proving restart/routing independence.
            async with httpx.AsyncClient(
                base_url=str(workers[(index + 1) % 2].base_url), cookies=client.cookies
            ) as other:
                replay = (
                    await other.post("/api/chat", headers=ORIGIN, json=data)
                ).json()
                answer = json.loads(replay["result"]["answer"])
                assert answer == {"question": f"guest-{index}", "history": []}
                history = (await other.get("/api/history")).json()["turns"]
                assert len(history) == 1 and history[0]["question"] == f"guest-{index}"

    tasks = [asyncio.create_task(guest(i)) for i in range(20)]
    peak = 0
    try:
        while any(not task.done() for task in tasks):
            async with pool.acquire() as conn:
                peak = max(
                    peak,
                    await conn.fetchval(
                        "SELECT count(*) FROM turns WHERE status='running'"
                    ),
                )
            await asyncio.sleep(0.02)
        await asyncio.gather(*tasks)
        assert peak == 20
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    async with pool.acquire() as conn:
        assert (
            await conn.fetchval("SELECT count(*) FROM turns WHERE status='completed'")
            == 20
        )
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM guest_sessions WHERE active_turn IS NOT NULL"
            )
            == 0
        )


@pytest.mark.parametrize("workers", [{"ACTIVE_AGENT_LIMIT": "1"}], indirect=True)
async def test_running_duplicate_competing_turn_cross_process_stop_and_shared_budget(
    workers, pool
):
    first, second = workers
    await start(first)
    second.cookies.update(first.cookies)
    data = {"turn_id": str(uuid.uuid4()), "message": "wait"}
    task = asyncio.create_task(first.post("/api/chat", headers=ORIGIN, json=data))
    url = f"/api/turns/{data['turn_id']}"
    try:
        for _ in range(100):
            response = await second.get(url)
            if response.status_code == 200:
                break
            await asyncio.sleep(0.02)
        assert response.json()["status"] == "running"
        duplicate = await second.post("/api/chat", headers=ORIGIN, json=data)
        assert duplicate.status_code == 202 and duplicate.json()["status_url"] == url
        assert (
            await second.post(
                "/api/chat", headers=ORIGIN, json={**data, "turn_id": str(uuid.uuid4())}
            )
        ).status_code == 409
        assert (await second.get("/api/history")).json()["active_turn"][
            "turn_id"
        ] == data["turn_id"]
        assert (await second.post(url + "/stop", headers=ORIGIN)).json()[
            "status"
        ] == "interrupted"
        response = await asyncio.wait_for(task, 3)
        assert "event: error" in response.text and "event: done" not in response.text
        # With only one process-local slot, this proves Stop released it.
        fresh = await first.post(
            "/api/chat",
            headers=ORIGIN,
            json={"turn_id": str(uuid.uuid4()), "message": "after Stop"},
        )
        assert "event: done" in fresh.text
        async with pool.acquire() as conn:
            assert await conn.fetchval("SELECT count(*) FROM turns") == 2
            assert (
                await conn.fetchval(
                    "SELECT used FROM rate_counters WHERE scope='turn-session:'||$1",
                    token_hash(first.cookies["hotel_session"]),
                )
                == 2
            )
            await conn.execute(
                "UPDATE rate_counters SET used=100 WHERE scope='turn-property-minute'"
            )
        rejected = await first.post(
            "/api/chat",
            headers=ORIGIN,
            json={"turn_id": str(uuid.uuid4()), "message": "over budget"},
        )
        assert rejected.status_code == 429
        rejected = await second.post(
            "/api/chat",
            headers=ORIGIN,
            json={"turn_id": str(uuid.uuid4()), "message": "over budget"},
        )
        assert rejected.status_code == 429
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_admission_overload_bypasses_health_and_releases_on_failure(client):
    await start(client)
    client.app.state.model_admission = ModelAdmission(1)
    client.app.state.model_admission.take()
    response = await client.post(
        "/api/chat",
        headers=ORIGIN,
        json={"turn_id": str(uuid.uuid4()), "message": "busy"},
    )
    assert response.status_code == 429 and response.headers["Retry-After"] == "5"
    assert (await client.get("/api/health")).status_code == 200
    assert (await client.get("/api/history")).status_code == 200
    client.app.state.model_admission.release()
    client.app.state.answer = result_model
    assert (
        "event: done"
        in (
            await client.post(
                "/api/chat",
                headers=ORIGIN,
                json={"turn_id": str(uuid.uuid4()), "message": "available"},
            )
        ).text
    )
    assert client.app.state.model_admission.active == 0


@pytest.mark.parametrize("workers", [{"TURN_TIMEOUT_SECONDS": "0.15"}], indirect=True)
async def test_application_deadline_is_failed_and_releases_admission(workers):
    client = workers[0]
    await start(client)
    data = {"turn_id": str(uuid.uuid4()), "message": "wait"}
    response = await client.post("/api/chat", headers=ORIGIN, json=data)
    assert "event: done" not in response.text
    assert (await client.get(f"/api/turns/{data['turn_id']}")).json()["status"] in (
        "failed",
        "interrupted",
    )
    assert (await client.get("/api/history")).json()["turns"] == []
    # A fresh attempt is admitted rather than retaining the previous lock.
    response = await client.post(
        "/api/chat", headers=ORIGIN, json={**data, "turn_id": str(uuid.uuid4())}
    )
    assert response.status_code == 200


async def test_killed_api_process_recovers_without_rerunning_turn(workers, pool):
    first, second = workers
    await start(first)
    second.cookies.update(first.cookies)
    turn_id = uuid.uuid4()
    task = asyncio.create_task(
        first.post(
            "/api/chat",
            headers=ORIGIN,
            json={"turn_id": str(turn_id), "message": "wait"},
        )
    )
    try:
        for _ in range(100):
            response = await second.get(f"/api/turns/{turn_id}")
            if response.status_code == 200:
                break
            await asyncio.sleep(0.02)
        assert response.json()["status"] == "running"
        first.worker_process.kill()
        first.worker_process.wait(timeout=5)
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE turns SET deadline_at=now()-interval '1 second' WHERE id=$1",
                turn_id,
            )
            await conn.execute(
                "UPDATE guest_sessions SET busy_until=now()-interval '1 second' WHERE active_turn=$1",
                turn_id,
            )
        assert (await second.get(f"/api/turns/{turn_id}")).json()[
            "status"
        ] == "interrupted"
        replay = await second.post(
            "/api/chat",
            headers=ORIGIN,
            json={"turn_id": str(turn_id), "message": "wait"},
        )
        assert replay.json()["status"] == "interrupted"
        fresh = await second.post(
            "/api/chat",
            headers=ORIGIN,
            json={"turn_id": str(uuid.uuid4()), "message": "after crash"},
        )
        assert "event: done" in fresh.text
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_committed_answer_is_not_cancelled_before_pool_release(client, pool):
    await start(client)
    client.app.state.answer = result_model
    delayed = False

    class Checkout:
        def __init__(self, checkout):
            self.checkout = checkout

        async def __aenter__(self):
            self.conn = await self.checkout.__aenter__()
            return self.conn

        async def __aexit__(self, *args):
            nonlocal delayed
            if not delayed and await self.conn.fetchval(
                "SELECT count(*) FROM turns WHERE status='completed'"
            ):
                delayed = True
                await asyncio.sleep(0.6)
            return await self.checkout.__aexit__(*args)

    class DelayedPool:
        def acquire(self, **kwargs):
            return Checkout(pool.acquire(**kwargs))

    client.app.state.pool = DelayedPool()
    try:
        response = await client.post(
            "/api/chat",
            headers=ORIGIN,
            json={"turn_id": str(uuid.uuid4()), "message": "complete"},
        )
        assert (
            delayed
            and "event: result" in response.text
            and "event: done" in response.text
        )
        assert client.app.state.model_admission.active == 0
    finally:
        client.app.state.pool = pool


async def test_watch_failure_stops_model_and_releases_admission(client, pool):
    await start(client)

    class FailedCheckout:
        async def __aenter__(self):
            raise TimeoutError("Injected watcher pool failure")

        async def __aexit__(self, *args):
            pass

    class WatchFailurePool:
        def acquire(self, **kwargs):
            if asyncio.current_task().get_name() == "hotel-turn-watch":
                return FailedCheckout()
            return pool.acquire(**kwargs)

    async def waiting(*args, **kwargs):
        yield {"type": "text", "text": "Partial"}
        await asyncio.Event().wait()

    client.app.state.pool = WatchFailurePool()
    client.app.state.answer = waiting
    turn_id = uuid.uuid4()
    try:
        response = await asyncio.wait_for(
            client.post(
                "/api/chat",
                headers=ORIGIN,
                json={"turn_id": str(turn_id), "message": "watch fails"},
            ),
            3,
        )
        assert "event: done" not in response.text and "event: error" in response.text
        assert (await client.get(f"/api/turns/{turn_id}")).json()["status"] == "failed"
        assert client.app.state.model_admission.active == 0
    finally:
        client.app.state.pool = pool


async def test_expired_rate_counters_are_pruned(pool):
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute(
            "INSERT INTO rate_counters VALUES ('old',now()-interval '1 day',1,now()-interval '1 hour')"
        )
        await budget(conn, [("live", 10, False)])
        assert (
            await conn.fetchval("SELECT count(*) FROM rate_counters WHERE scope='old'")
            == 0
        )
        assert (
            await conn.fetchval("SELECT used FROM rate_counters WHERE scope='live'")
            == 1
        )
