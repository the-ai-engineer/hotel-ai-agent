import asyncio
import os
import socket
import subprocess
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text


@pytest.fixture
async def workers(db):
    async with db.transaction() as c:
        await c.execute(
            text(
                "CREATE TABLE IF NOT EXISTS test_model_receipts(id uuid PRIMARY KEY,calls int NOT NULL)"
            )
        )
        await c.execute(text("TRUNCATE test_model_receipts"))
    processes, urls = [], []
    try:
        for _ in range(2):
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            urls.append(f"http://127.0.0.1:{port}")
            processes.append(
                subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "process_app:create_app",
                        "--factory",
                        "--app-dir",
                        "tests",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                        "--no-proxy-headers",
                        "--no-access-log",
                    ],
                    cwd=Path(__file__).parents[1],
                    env=os.environ.copy(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            )
        async with httpx.AsyncClient() as client:
            for url in urls:
                for _ in range(100):
                    try:
                        if (await client.get(url + "/health/ready", timeout=1)).status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    await asyncio.sleep(0.1)
                else:
                    raise AssertionError("Test worker failed to start")
        yield urls
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                await asyncio.to_thread(process.wait, timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                await asyncio.to_thread(process.wait, timeout=5)


async def test_two_processes_share_ownership_and_execute_once(workers, db):
    async with AsyncExitStack() as stack:
        clients = [
            await stack.enter_async_context(
                httpx.AsyncClient(base_url=url, headers={"Origin": "http://test.hotel"}, timeout=10)
            )
            for url in workers
        ]
        session = await clients[0].post("/api/session", json={})
        assert session.status_code == 200
        cookie = session.headers["set-cookie"].split(";", 1)[0]
        for client in clients:
            client.headers["Cookie"] = cookie
        conversation = (await clients[0].post("/api/conversations", json={})).json()["id"]
        id = uuid4()
        body = {"client_turn_id": str(id), "message": f"breakfast {id}"}
        path = f"/api/conversations/{conversation}/turns"
        responses = await asyncio.gather(*(c.post(path, json=body) for c in clients))
        assert sorted(r.status_code for r in responses) == [200, 409]
        assert "event: done" in (await clients[1].post(path, json=body)).text
        assert (await clients[1].get(path + f"/{id}")).json()["state"] == "completed"
        clients[1].headers.pop("Cookie")
        assert (await clients[1].get(f"/api/conversations/{conversation}")).status_code == 401
        async with db.transaction() as c:
            assert (
                await c.execute(
                    text("SELECT calls FROM test_model_receipts WHERE id=:id"), {"id": id}
                )
            ).scalar_one() == 1


async def test_independent_guests_run_across_two_processes(workers, db):
    async def guest(index):
        async with httpx.AsyncClient(
            base_url=workers[index % 2], headers={"Origin": "http://test.hotel"}, timeout=10
        ) as client:
            session = await client.post("/api/session", json={})
            client.headers["Cookie"] = session.headers["set-cookie"].split(";", 1)[0]
            conversation = (await client.post("/api/conversations", json={})).json()["id"]
            marker = uuid4()
            response = await client.post(
                f"/api/conversations/{conversation}/turns",
                json={"client_turn_id": str(marker), "message": f"breakfast {marker}"},
            )
            assert response.status_code == 200 and "event: done" in response.text
            return conversation, client.headers["Cookie"], marker

    records = await asyncio.gather(*(guest(i) for i in range(8)))
    async with httpx.AsyncClient(
        base_url=workers[1], headers={"Origin": "http://test.hotel", "Cookie": records[0][1]}
    ) as client:
        assert (await client.get(f"/api/conversations/{records[1][0]}")).status_code == 404
    async with db.transaction() as c:
        receipts = (await c.execute(text("SELECT calls FROM test_model_receipts"))).scalars().all()
        assert len(receipts) == 8 and all(count == 1 for count in receipts)
