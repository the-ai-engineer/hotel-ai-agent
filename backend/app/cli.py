import argparse
import asyncio
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

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
    finally:
        await db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seed"])
    parser.parse_args()
    asyncio.run(seed(Settings()))


if __name__ == "__main__":
    main()
