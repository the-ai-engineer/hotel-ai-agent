import argparse
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy import text

from .config import Settings
from .db import Database


async def seed(settings):
    if settings.app_env == "production":
        raise ValueError("Demo seeds are forbidden in production")
    db = Database(settings.database_url)
    try:
        async with db.transaction() as connection:
            policies = json.loads(
                (Path(__file__).resolve().parents[1] / "seeds/policies.json").read_text()
            )
            for policy in policies:
                slug, title, body = policy["slug"], policy["title"], policy["body"]
                id = uuid5(NAMESPACE_URL, "sanctuary/policy/" + slug + "/1")
                await connection.execute(
                    text("""
                    INSERT INTO policy_versions(id,slug,title,version,published)
                    VALUES(:id,:slug,:title,1,true) ON CONFLICT(id) DO NOTHING
                """),
                    {"id": id, "slug": slug, "title": title},
                )
                await connection.execute(
                    text("""
                    INSERT INTO policy_sections(id,version_id,position,body)
                    VALUES(:section,:version,1,:body) ON CONFLICT(id) DO NOTHING
                """),
                    {"section": uuid5(id, "section/1"), "version": id, "body": body},
                )
            today = datetime.now(ZoneInfo(settings.hotel_timezone)).date()
            end = today + timedelta(days=365)
            villas = json.loads(
                (Path(__file__).resolve().parents[1] / "seeds/villas.json").read_text()
            )
            # Re-seeding is explicit; replace only this demo property's occupancy.
            ids = [uuid5(NAMESPACE_URL, "sanctuary/villa/" + villa["slug"]) for villa in villas]
            await connection.execute(
                text("DELETE FROM bookings WHERE villa_id=ANY(CAST(:ids AS uuid[]))"), {"ids": ids}
            )
            await connection.execute(
                text("DELETE FROM inventory_days WHERE villa_id=ANY(CAST(:ids AS uuid[]))"),
                {"ids": ids},
            )
            for villa in villas:
                id = uuid5(NAMESPACE_URL, "sanctuary/villa/" + villa["slug"])
                await connection.execute(
                    text("""INSERT INTO villas(id,slug,name,description,capacity,amenities,image)
                    VALUES(:id,:slug,:name,:description,:capacity,CAST(:amenities AS jsonb),:image)
                    ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name,description=EXCLUDED.description,capacity=EXCLUDED.capacity,amenities=EXCLUDED.amenities,image=EXCLUDED.image"""),
                    {**villa, "id": id, "amenities": json.dumps(villa["amenities"])},
                )
                await connection.execute(
                    text("""INSERT INTO inventory_days(villa_id,day)
                    SELECT :id,d::date FROM generate_series(CAST(:start AS date),CAST(:end AS date)-1,interval '1 day') AS d"""),
                    {"id": id, "start": today, "end": end},
                )
            await connection.execute(
                text("""INSERT INTO demo_inventory VALUES(1,:start,:end)
                ON CONFLICT(id) DO UPDATE SET starts_on=EXCLUDED.starts_on,ends_on=EXCLUDED.ends_on"""),
                {"start": today, "end": end},
            )
            await connection.execute(
                text("""INSERT INTO bookings(id,villa_id,check_in,check_out,status)
                VALUES(:id,:villa,:start,:end,'blocking')"""),
                {
                    "id": uuid5(NAMESPACE_URL, "sanctuary/demo-booking"),
                    "villa": uuid5(NAMESPACE_URL, "sanctuary/villa/forest-suite"),
                    "start": today + timedelta(days=7),
                    "end": today + timedelta(days=10),
                },
            )
    finally:
        await db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seed"])
    parser.parse_args()
    asyncio.run(seed(Settings()))


if __name__ == "__main__":
    main()
