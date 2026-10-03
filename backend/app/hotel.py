import re
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text

from .schemas import Availability, Source, Villa


async def search_policies(db, query: str) -> list[dict]:
    if not isinstance(query, str) or not query.strip() or len(query) > 200:
        return []
    async with db.transaction() as connection:
        rows = (
            (
                await connection.execute(
                    text("""
            SELECT v.id,v.slug,v.title,v.version,left(s.body,2000) AS passage
            FROM policy_versions v JOIN policy_sections s ON s.version_id=v.id
            WHERE v.published AND NOT v.superseded
              AND s.search_vector @@ websearch_to_tsquery('english',:query)
            ORDER BY ts_rank(s.search_vector,websearch_to_tsquery('english',:query)) DESC,
                     v.slug,s.position
            LIMIT 5
        """),
                    {"query": query.strip()},
                )
            )
            .mappings()
            .all()
        )
    return [
        {
            "source": Source(
                id=row["id"],
                title=row["title"],
                version=row["version"],
                url=f"/policies/{row['slug']}?version={row['version']}",
            ).model_dump(mode="json"),
            "passage": row["passage"],
        }
        for row in rows
    ]


async def policy_page(db, slug: str, version: int | None):
    async with db.transaction() as connection:
        rows = (
            (
                await connection.execute(
                    text("""
            SELECT v.title,v.version,v.superseded,s.body
            FROM policy_versions v JOIN policy_sections s ON s.version_id=v.id
            WHERE v.slug=:slug AND v.published
              AND ((CAST(:version AS integer) IS NULL AND NOT v.superseded) OR v.version=CAST(:version AS integer))
            ORDER BY s.position
        """),
                    {"slug": slug, "version": version},
                )
            )
            .mappings()
            .all()
        )
    return rows


async def catalogue(db):
    async with db.transaction() as c:
        rows = (
            (
                await c.execute(
                    text("SELECT slug,name FROM villas WHERE active ORDER BY slug LIMIT 21")
                )
            )
            .mappings()
            .all()
        )
    if len(rows) > 20:
        raise ValueError("V1 catalogue supports at most twenty physical villas")
    return [dict(row) for row in rows]


def villa_from_row(row):
    return Villa.model_validate(dict(row))


async def get_villa(db, slug: str):
    if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9-]{1,80}", slug):
        return None
    async with db.transaction() as c:
        row = (
            (
                await c.execute(
                    text(
                        "SELECT slug,name,description,capacity,amenities,image FROM villas WHERE active AND slug=:slug"
                    ),
                    {"slug": slug},
                )
            )
            .mappings()
            .one_or_none()
        )
    return villa_from_row(row) if row else None


async def check_availability(db, settings, check_in: str, check_out: str, guests: int):
    if not all(
        isinstance(d, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in [check_in, check_out]
    ):
        raise ValueError("Use exact YYYY-MM-DD dates")
    start, end = date.fromisoformat(check_in), date.fromisoformat(check_out)
    today = datetime.now(ZoneInfo(settings.hotel_timezone)).date()
    if (
        type(guests) is not int
        or not 1 <= guests <= 8
        or start < today
        or not 1 <= (end - start).days <= 30
    ):
        raise ValueError("Stay must be 1–30 nights, begin today or later and have 1–8 guests")
    async with db.transaction() as c:
        await c.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        horizon = (
            (await c.execute(text("SELECT starts_on,ends_on FROM demo_inventory WHERE id=1")))
            .mappings()
            .one_or_none()
        )
        if not horizon:
            raise RuntimeError("Demo inventory is not seeded")
        data = dict(
            check_in=start,
            check_out=end,
            guests=guests,
            checked_at=datetime.now(UTC),
            horizon_start=horizon["starts_on"],
            horizon_end=horizon["ends_on"],
        )
        if start < horizon["starts_on"] or end > horizon["ends_on"]:
            return Availability(outcome="outside_demo_period", **data)
        rows = (
            (
                await c.execute(
                    text("""
            SELECT v.slug,v.name,v.description,v.capacity,v.amenities,v.image
            FROM villas v
            WHERE v.active AND v.capacity>=:guests
              AND (SELECT count(*) FROM inventory_days d WHERE d.villa_id=v.id AND d.open
                   AND d.day>=:start AND d.day<:end)=:nights
              AND NOT EXISTS(SELECT 1 FROM bookings b WHERE b.villa_id=v.id AND b.status='blocking'
                             AND b.check_in<:end AND b.check_out>:start)
            ORDER BY v.slug LIMIT 7
        """),
                    {"guests": guests, "start": start, "end": end, "nights": (end - start).days},
                )
            )
            .mappings()
            .all()
        )
    return Availability(
        outcome="ok" if rows else "no_matches",
        villas=[villa_from_row(row) for row in rows[:6]],
        more_available=len(rows) > 6,
        **data,
    )
