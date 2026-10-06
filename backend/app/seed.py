import json
import re


async def import_policies(pool, source):
    rows = []
    ids = set()
    for entry in json.loads((source / "catalogue.json").read_text()):
        document_id = entry["id"]
        path = (source / entry["file"]).resolve()
        if not path.is_relative_to(source.resolve()) or document_id in ids:
            raise ValueError(
                "Policy path must stay within hotel/ and IDs must be unique."
            )
        ids.add(document_id)
        body = path.read_text()
        match = re.search(
            r"Document ID: ([\w-]+) \| Revision: (\d+) \| Status: (published|unpublished)",
            body,
        )
        if (
            not match
            or match[1] != document_id
            or body.splitlines()[0] != "# " + entry["title"]
        ):
            raise ValueError(f"Invalid policy header: {document_id}")
        if len(body) > 6000:
            raise ValueError(
                f"{document_id}: shorten the complete policy to 6000 characters."
            )
        rows.append(
            {
                **entry,
                "revision": int(match[2]),
                "body": body,
                "published": match[3] == "published",
            }
        )
    public = [
        {k: row[k] for k in ("id", "title", "summary", "keywords", "revision")}
        for row in rows
        if row["published"]
    ]
    if len(public) > 20 or len(json.dumps(public)) > 6000:
        raise ValueError("Published catalogue exceeds 20 documents or 6000 characters.")
    async with pool.acquire(timeout=3) as conn, conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(431298)")
        for row in rows:
            existing = await conn.fetchrow(
                "SELECT * FROM documents WHERE id=$1 AND revision=$2",
                row["id"],
                row["revision"],
            )
            if existing and any(
                existing[k] != row[k] for k in ("title", "summary", "body")
            ):
                raise ValueError(
                    f"{row['id']}: increment revision before changing content."
                )
            if existing and json.loads(existing["keywords"]) != row["keywords"]:
                raise ValueError(
                    f"{row['id']}: increment revision before changing keywords."
                )
            # Withdrawal makes every version unavailable; old published revisions otherwise remain readable.
            if not row["published"]:
                await conn.execute(
                    "UPDATE documents SET published=false WHERE id=$1", row["id"]
                )
            await conn.execute(
                """INSERT INTO documents VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7)
                ON CONFLICT (id,revision) DO UPDATE SET published=excluded.published""",
                row["id"],
                row["revision"],
                row["title"],
                row["summary"],
                json.dumps(row["keywords"]),
                row["body"],
                row["published"],
            )
        await conn.execute(
            "UPDATE documents SET published=false WHERE NOT (id=ANY($1::text[]))",
            list(ids),
        )
