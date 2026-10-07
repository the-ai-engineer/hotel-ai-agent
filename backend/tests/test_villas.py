from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from sqlalchemy import text

from app import hotel
from app.agent import Concierge
from app.config import Settings
from app.tools import Evidence, policy_tools


def today():
    return datetime.now(ZoneInfo("Asia/Makassar")).date()


def dates(a, b):
    return str(today() + timedelta(days=a)), str(today() + timedelta(days=b))


async def lookup(db, a, b, guests=2):
    return await hotel.check_availability(db, Settings(_env_file=None), *dates(a, b), guests)


def slugs(result):
    return {v.slug for v in result.villas}


async def test_checkout_exclusive_and_blocking_overlap(db):
    assert "forest-suite" in slugs(await lookup(db, 6, 7))
    assert "forest-suite" not in slugs(await lookup(db, 7, 8))
    assert "forest-suite" not in slugs(await lookup(db, 8, 10))
    assert "forest-suite" in slugs(await lookup(db, 10, 11))
    async with db.transaction() as c:
        await c.execute(text("UPDATE bookings SET status='cancelled'"))
    assert "forest-suite" in slugs(await lookup(db, 7, 8))


async def test_missing_closed_nights_and_guest_capacity(db):
    async with db.transaction() as c:
        await c.execute(
            text(
                "DELETE FROM inventory_days WHERE villa_id=(SELECT id FROM villas WHERE slug='forest-suite') AND day=:day"
            ),
            {"day": today() + timedelta(days=3)},
        )
    assert "forest-suite" not in slugs(await lookup(db, 2, 4))
    assert slugs(await lookup(db, 2, 4, 5)) == {"canopy-villa"}
    async with db.transaction() as c:
        await c.execute(
            text(
                "UPDATE inventory_days SET open=false WHERE villa_id=(SELECT id FROM villas WHERE slug='canopy-villa') AND day=:day"
            ),
            {"day": today() + timedelta(days=3)},
        )
    assert (await lookup(db, 2, 4, 5)).outcome == "no_matches"


@pytest.mark.parametrize(
    "a,b,guests", [(-1, 1, 2), (1, 1, 2), (1, 33, 2), (1, 2, 0), (1, 2, 9), (1, 2, True)]
)
async def test_invalid_stays(db, a, b, guests):
    with pytest.raises(ValueError):
        await lookup(db, a, b, guests)


async def test_demo_horizon_and_public_villa_details(db):
    assert (await lookup(db, 364, 365)).outcome == "ok"
    assert (await lookup(db, 365, 366)).outcome == "outside_demo_period"
    villa = await hotel.get_villa(db, "forest-suite")
    assert villa.capacity == 2 and "id" not in villa.model_dump()
    assert await hotel.get_villa(db, "unknown") is None
    assert await hotel.get_villa(db, "'; DROP TABLE villas") is None


async def test_failed_later_lookup_clears_earlier_cards(db):
    evidence = Evidence()
    tool = policy_tools(db, evidence, Settings(_env_file=None))[2]
    assert (await tool(*dates(2, 4), 2))["outcome"] == "ok"
    assert evidence.availability is not None
    assert (await tool("not-a-date", "not-a-date", 2))["outcome"] == "invalid_input"
    assert evidence.availability is None


class AvailabilityModel(BaseLlm):
    model: str = "test-availability"

    async def generate_content_async(self, llm_request, stream=False):
        last = llm_request.contents[-1]
        if any(p.function_response for p in last.parts):
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text="Here are the available villas. This does not make a reservation."
                        )
                    ],
                )
            )
        else:
            start, end = dates(2, 4)
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="check_availability",
                                args={"check_in": start, "check_out": end, "guests": 2},
                            )
                        )
                    ],
                )
            )


async def test_actual_adk_availability_produces_server_cards(db):
    concierge = Concierge(
        Settings(_env_file=None, google_cloud_project=""), db, AvailabilityModel()
    )
    events = [e async for e in concierge.run(uuid4(), "Two guests for two nights", [])]
    result = events[-1]["data"]
    assert result["availability"]["outcome"] == "ok"
    assert len(result["cards"]) == 3
    assert {v["slug"] for v in result["cards"]} == {"forest-suite", "garden-villa", "canopy-villa"}
    assert "id" not in result["cards"][0]
    assert "villas" not in result["availability"]


async def test_exact_stay_boundaries(db):
    assert (await lookup(db, 0, 1, 1)).outcome == "ok"
    assert (await lookup(db, 1, 31, 1)).outcome == "ok"
    assert (await lookup(db, 1, 2, 8)).outcome == "no_matches"
    with pytest.raises(hotel.InvalidStay):
        await lookup(db, 1, 32, 2)


async def test_integral_float_and_data_fault_classification(db):
    evidence = Evidence()
    tool = policy_tools(db, evidence, Settings(_env_file=None))[2]
    assert (await tool(*dates(2, 4), 2.0))["outcome"] == "ok"
    async with db.transaction() as c:
        await c.execute(text("UPDATE villas SET image='javascript:bad'"))
    assert (await tool(*dates(2, 4), 2))["outcome"] == "unavailable"
    assert evidence.availability is None


async def test_parallel_lookup_cannot_restore_stale_cards(db, monkeypatch):
    import asyncio

    result = await lookup(db, 2, 4)
    started, release = asyncio.Event(), asyncio.Event()

    async def delayed(db, settings, start, end, guests):
        if start == "older":
            started.set()
            await release.wait()
            return result
        raise hotel.InvalidStay("newer invalid input")

    monkeypatch.setattr(hotel, "check_availability", delayed)
    evidence = Evidence()
    tool = policy_tools(db, evidence, Settings(_env_file=None))[2]
    older = asyncio.create_task(tool("older", "end", 2))
    await started.wait()
    assert (await tool("newer", "end", 2))["outcome"] == "invalid_input"
    release.set()
    await older
    assert evidence.availability is None


async def test_read_only_checkout_does_not_poison_pool(db):
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError):
        async with db.transaction(read_only=True) as c:
            await c.execute(text("UPDATE villas SET active=false"))
    async with db.transaction() as c:
        await c.execute(text("UPDATE villas SET active=true"))
    assert len(await hotel.catalogue(db)) == 3
