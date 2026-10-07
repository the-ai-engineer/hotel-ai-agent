import json
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

VillaID = Annotated[str, Field(pattern=r"^[a-z0-9-]+$", max_length=80)]


class Villa(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: VillaID
    name: str = Field(min_length=1, max_length=100)
    capacity: int = Field(ge=1, le=8)
    bedrooms: int = Field(ge=1, le=4)
    private_pool: bool
    pool_fenced: bool
    image: str = Field(pattern=r"^assets/[a-z0-9-]+\.png$")
    description: str = Field(max_length=1000)
    amenities: list[str] = Field(max_length=10)
    beds: list[str] = Field(min_length=1, max_length=8)


class InventoryDay(BaseModel):
    villa_id: VillaID
    night: date
    open: bool


class Booking(BaseModel):
    villa_id: VillaID
    check_in: date
    check_out: date
    status: Literal["confirmed", "cancelled"]


async def import_inventory(pool, source):
    villas = [
        Villa.model_validate(row)
        for row in json.loads((source / "villas.json").read_text())
    ]
    inventory = json.loads((source / "availability.json").read_text())
    days = [InventoryDay.model_validate(row) for row in inventory["inventory_days"]]
    bookings = [Booking.model_validate(row) for row in inventory["bookings"]]
    ids = {villa.id for villa in villas}
    if (
        not villas
        or len(ids) != len(villas)
        or len({(day.villa_id, day.night) for day in days}) != len(days)
    ):
        raise ValueError("Villa IDs and inventory nights must be unique.")
    if any(row.villa_id not in ids for row in [*days, *bookings]):
        raise ValueError("Inventory must reference a known villa.")
    if any(booking.check_out <= booking.check_in for booking in bookings):
        raise ValueError("Booking checkout must follow check-in.")
    if any(
        not (source.parent / "frontend" / villa.image).is_file() for villa in villas
    ):
        raise ValueError("Villa images must reference an approved existing site asset.")
    if horizon := inventory.get("horizon"):
        start, end = (
            date.fromisoformat(horizon["start"]),
            date.fromisoformat(horizon["end"]),
        )
        if not 1 <= (end - start).days <= 730 or any(
            not start <= row.night < end for row in days
        ):
            raise ValueError(
                "Inventory horizon must contain all explicit nights and span at most two years."
            )
        overrides = {(row.villa_id, row.night): row.open for row in days}
        days = [
            InventoryDay(
                villa_id=villa.id,
                night=start + timedelta(days=n),
                open=overrides.get((villa.id, start + timedelta(days=n)), True),
            )
            for villa in villas
            for n in range((end - start).days)
        ]
    async with pool.acquire(timeout=3) as conn, conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(431299)")
        for villa_id in sorted(ids):
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
                f"villa:{villa_id}",
            )
        # Explicit fictional fixture import; retain guest reservations.
        await conn.execute("DELETE FROM bookings WHERE reference IS NULL")
        await conn.execute("DELETE FROM inventory_days")
        for villa in villas:
            await conn.execute(
                """INSERT INTO villas VALUES ($1,$2,$3::jsonb)
                ON CONFLICT (id) DO UPDATE SET capacity=excluded.capacity,data=excluded.data""",
                villa.id,
                villa.capacity,
                villa.model_dump_json(),
            )
        await conn.execute(
            "DELETE FROM villas WHERE NOT(id=ANY($1::text[]))", list(ids)
        )
        await conn.executemany(
            "INSERT INTO inventory_days VALUES ($1,$2,$3)",
            [(row.villa_id, row.night, row.open) for row in days],
        )
        await conn.executemany(
            "INSERT INTO bookings(villa_id,check_in,check_out,status) VALUES ($1,$2,$3,$4)",
            [
                (row.villa_id, row.check_in, row.check_out, row.status)
                for row in bookings
            ],
        )


async def get_villa(pool, villa_id):
    async with pool.acquire(timeout=3) as conn:
        data = await conn.fetchval("SELECT data FROM villas WHERE id=$1", villa_id)
    return json.loads(data) if data else None


async def check_availability(pool, check_in, check_out, guests):
    async with pool.acquire(timeout=3) as conn:
        return await availability_on_connection(conn, check_in, check_out, guests)


async def availability_on_connection(conn, check_in, check_out, guests):
    try:
        start, end = date.fromisoformat(check_in), date.fromisoformat(check_out)
        if start.isoformat() != check_in or end.isoformat() != check_out:
            raise ValueError()
    except (ValueError, TypeError):
        return {
            "error": "invalid_dates",
            "message": "Use exact dates in YYYY-MM-DD format.",
        }
    nights = (end - start).days
    if type(guests) is not int or not 1 <= guests <= 8 or not 1 <= nights <= 30:
        return {
            "error": "invalid_stay",
            "message": "Provide 1–8 guests including children and infants, and a stay of 1–30 nights.",
        }
    result = {
        "check_in": check_in,
        "check_out": check_out,
        "guests": guests,
        "nights": nights,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "cards": [],
    }
    horizon = await conn.fetchrow(
        "SELECT min(night) AS first,max(night) AS last FROM inventory_days"
    )
    if (
        not horizon["first"]
        or start < horizon["first"]
        or end.toordinal() - 1 > horizon["last"].toordinal()
    ):
        return {
            **result,
            "status": "unknown_inventory",
            "message": "These dates are outside the fictional inventory. Availability is unknown.",
        }
    rows = await conn.fetch(
        """SELECT v.data FROM villas v WHERE v.capacity >= $3
        AND (SELECT count(*) FROM inventory_days d WHERE d.villa_id=v.id
            AND d.night >= $1 AND d.night < $2 AND d.open) = $4
        AND NOT EXISTS (SELECT 1 FROM bookings b WHERE b.villa_id=v.id
            AND b.status='confirmed' AND b.check_in < $2 AND b.check_out > $1)
        ORDER BY v.capacity,v.id""",
        start,
        end,
        guests,
        nights,
    )
    cards = [json.loads(row["data"]) for row in rows]
    return {**result, "status": "available" if cards else "no_match", "cards": cards}
