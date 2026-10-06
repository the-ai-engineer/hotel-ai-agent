import asyncio
import uuid
from datetime import date
from pathlib import Path

import httpx
import pytest

from app import reservations
from app.db import token_hash
from app.inventory import import_inventory
from app.tools import HotelTools

ORIGIN = {"Origin": "http://127.0.0.1:8773"}
DETAILS = {
    "villa_id": "forest-suite",
    "check_in": "2026-10-10",
    "check_out": "2026-10-11",
    "guests": 2,
}


@pytest.fixture(autouse=True)
def fixed_booking_date(monkeypatch):
    monkeypatch.setattr(reservations, "property_today", lambda: date(2026, 10, 6))


async def start(client):
    assert (await client.post("/api/session", headers=ORIGIN)).status_code == 200


async def book(client, **changes):
    payload = {**DETAILS, "request_id": str(uuid.uuid4()), **changes}
    response = await client.post("/api/bookings", headers=ORIGIN, json=payload)
    return response, payload


async def test_booking_explicit_confirmation_idempotency_and_availability(client, pool):
    await start(client)
    assert (await client.get("/book")).status_code == 200
    result = (await client.get("/api/availability", params=DETAILS)).json()
    assert result["status"] == "available"
    async with pool.acquire() as conn:
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM bookings WHERE reference IS NOT NULL"
            )
            == 0
        )
    response, payload = await book(client)
    assert response.status_code == 200
    booking = response.json()["booking"]
    repeated = await client.post("/api/bookings", headers=ORIGIN, json=payload)
    assert repeated.json()["booking"] == booking
    assert (await client.get(f"/api/bookings/{booking['reference']}")).json()[
        "booking"
    ] == booking
    changed = await client.post(
        "/api/bookings", headers=ORIGIN, json={**payload, "guests": 1}
    )
    assert changed.status_code == 409
    result = (await client.get("/api/availability", params=DETAILS)).json()
    assert [card["id"] for card in result["cards"]] == ["garden-villa"]
    assert (await client.post("/api/conversation", headers=ORIGIN)).status_code == 200
    assert (
        await client.get(f"/api/bookings/{booking['reference']}")
    ).status_code == 200


async def test_concurrent_overlap_allows_one_booking_and_seed_preserves_it(pool):
    async with pool.acquire() as conn:
        await conn.executemany(
            "INSERT INTO guest_sessions(token_hash) VALUES($1)", [("one",), ("two",)]
        )
    results = await asyncio.gather(
        reservations.reserve(pool, "one", uuid.uuid4(), **DETAILS),
        reservations.reserve(pool, "two", uuid.uuid4(), **DETAILS),
        return_exceptions=True,
    )
    assert sum(isinstance(result, dict) for result in results) == 1
    assert (
        sum(isinstance(result, reservations.ReservationError) for result in results)
        == 1
    )
    await import_inventory(pool, Path(__file__).resolve().parents[2] / "hotel")
    async with pool.acquire() as conn:
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM bookings WHERE reference IS NOT NULL"
            )
            == 1
        )


async def test_booking_ownership_origin_capacity_and_past_dates(client):
    await start(client)
    response, _ = await book(client)
    reference = response.json()["booking"]["reference"]
    async with httpx.AsyncClient(
        transport=client._transport, base_url="http://127.0.0.1:8773"
    ) as other:
        await start(other)
        assert (await other.get(f"/api/bookings/{reference}")).status_code == 404
        assert (await other.get("/api/bookings/unknown")).status_code == 404
    assert (
        await client.post(
            "/api/bookings",
            headers={"Origin": "https://evil.example"},
            json={**DETAILS, "request_id": str(uuid.uuid4())},
        )
    ).status_code == 403
    assert (
        await book(client, check_in="2026-11-01", check_out="2026-11-03", guests=4)
    )[0].status_code == 409
    assert (await book(client, check_in="2026-10-01", check_out="2026-10-02"))[
        0
    ].status_code == 409


async def proposed_note(client, reference):
    async def fake(pool, settings, history, question, guest=None):
        tools = HotelTools(pool, guest)
        assert (await tools.lookup_booking(reference))["booking"][
            "reference"
        ] == reference
        await tools.prepare_hotel_request(
            reference,
            "Please review late checkout until 14:00. I understand it needs approval.",
        )
        yield {
            "type": "result",
            "answer": "Review the note below.",
            "sources": [],
            "hotel_request": tools.hotel_request,
        }

    client.app.state.answer = fake
    response = await client.post(
        "/api/chat",
        headers=ORIGIN,
        json={"turn_id": str(uuid.uuid4()), "message": "Request late checkout"},
    )
    assert "event: done" in response.text
    return (await client.get("/api/history")).json()["turns"][-1]["hotel_request"]


async def test_note_draft_confirmation_ownership_and_idempotency(client, pool):
    await start(client)
    response, _ = await book(client)
    reference = response.json()["booking"]["reference"]
    request = await proposed_note(client, reference)
    assert request["status"] == "draft"
    url = f"/api/requests/{request['id']}/confirm"
    async with httpx.AsyncClient(
        transport=client._transport, base_url="http://127.0.0.1:8773"
    ) as other:
        await start(other)
        assert (await other.post(url, headers=ORIGIN)).status_code == 409
        tools = HotelTools(
            pool,
            {
                "session_hash": token_hash(other.cookies["hotel_session"]),
                "conversation_id": str(uuid.uuid4()),
            },
        )
        assert "error" in await tools.lookup_booking(reference)
        assert "error" in await tools.prepare_hotel_request(reference, "Cannot send")
    sent = await client.post(url, headers=ORIGIN)
    assert sent.status_code == 200 and sent.json()["status"] == "pending_review"
    assert (await client.post(url, headers=ORIGIN)).json() == sent.json()
    assert (await client.get("/api/history")).json()["turns"][-1]["hotel_request"][
        "status"
    ] == "pending_review"
    assert (await client.get(f"/api/bookings/{reference}")).json()["booking"][
        "check_out"
    ] == DETAILS["check_out"]


async def test_reset_expiry_supersession_and_failed_stream_cannot_send_notes(
    client, pool
):
    await start(client)
    response, _ = await book(client)
    reference = response.json()["booking"]["reference"]
    old = await proposed_note(client, reference)
    current = await proposed_note(client, reference)
    assert (
        await client.post(f"/api/requests/{old['id']}/confirm", headers=ORIGIN)
    ).status_code == 409
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE hotel_requests SET expires_at=now()-interval '1 second' WHERE id=$1",
            uuid.UUID(current["id"]),
        )
    assert (
        await client.post(f"/api/requests/{current['id']}/confirm", headers=ORIGIN)
    ).status_code == 409
    reset = await proposed_note(client, reference)
    await client.post("/api/conversation", headers=ORIGIN)
    assert (
        await client.post(f"/api/requests/{reset['id']}/confirm", headers=ORIGIN)
    ).status_code == 409

    async def fail(pool, settings, history, question, guest=None):
        tools = HotelTools(pool, guest)
        await tools.lookup_booking(reference)
        await tools.prepare_hotel_request(reference, "This draft must never be saved")
        raise RuntimeError("model failed")
        yield

    client.app.state.answer = fail
    await client.post(
        "/api/chat",
        headers=ORIGIN,
        json={"turn_id": str(uuid.uuid4()), "message": "Prepare note"},
    )
    async with pool.acquire() as conn:
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM hotel_requests WHERE note=$1",
                "This draft must never be saved",
            )
            == 0
        )
