from datetime import date

import pytest

from app.inventory import check_availability, get_villa
from app.tools import HotelTools


@pytest.mark.parametrize(
    "start,end,guests,ids",
    [
        ("2026-11-01", "2026-11-04", 4, ["garden-villa"]),
        ("2026-11-03", "2026-11-05", 2, ["garden-villa"]),
        ("2026-11-05", "2026-11-07", 4, []),
        ("2026-11-01", "2026-11-03", 2, ["forest-suite", "garden-villa"]),
        ("2026-11-05", "2026-11-06", 2, ["forest-suite"]),
    ],
)
async def test_full_stay_overlap_adjacency_closure_and_cancelled_booking(
    pool, start, end, guests, ids
):
    result = await check_availability(pool, start, end, guests)
    assert [card["id"] for card in result["cards"]] == ids
    assert result["check_in"] == start and result["check_out"] == end
    assert (
        result["nights"] == (date.fromisoformat(end) - date.fromisoformat(start)).days
    )
    assert result["checked_at"] and all("price" not in card for card in result["cards"])


async def test_missing_night_is_unavailable_and_outside_horizon_is_unknown(pool):
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM inventory_days WHERE villa_id='garden-villa' AND night='2026-11-02'"
        )
    assert (await check_availability(pool, "2026-11-01", "2026-11-04", 4))[
        "cards"
    ] == []
    result = await check_availability(pool, "2027-11-10", "2027-11-12", 2)
    assert result["status"] == "unknown_inventory" and result["cards"] == []


@pytest.mark.parametrize(
    "start,end,guests",
    [
        ("next week", "2026-11-03", 2),
        ("20261101", "2026-11-03", 2),
        ("2026-11-03", "2026-11-01", 2),
        ("2026-11-01", "2026-11-01", 2),
        ("2026-11-01", "2026-11-03", 0),
        ("2026-11-01", "2026-11-03", True),
    ],
)
async def test_invalid_stay_has_no_cards(pool, start, end, guests):
    result = await check_availability(pool, start, end, guests)
    assert "error" in result and "cards" not in result


async def test_villa_facts_and_invocation_card_isolation(pool):
    villa = await get_villa(pool, "garden-villa")
    assert villa["capacity"] == 4 and villa["beds"] == ["1 king bed", "2 single beds"]
    assert villa["pool_fenced"] is False
    assert await get_villa(pool, "unknown") is None
    one, two = HotelTools(pool), HotelTools(pool)
    await one.check_availability("2026-11-01", "2026-11-04", 4)
    assert one.availability["cards"][0]["id"] == "garden-villa"
    assert two.availability is None
    await one.check_availability("next week", "2026-11-04", 4)
    assert one.availability is None


async def test_near_term_inventory_includes_october_weekend(pool):
    result = await check_availability(pool, "2026-10-10", "2026-10-11", 2)
    assert result["status"] == "available"
    assert len(result["cards"]) == 2
