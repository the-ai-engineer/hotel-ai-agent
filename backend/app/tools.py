import json

from app import inventory


class HotelTools:
    """One invocation's read-only tools and evidence. Never shared between guests."""

    def __init__(self, pool):
        self.pool = pool
        self.sources = {}
        self.calls = 0
        self.characters = 0
        self.listed = set()
        self.availability = None

    def admit(self):
        self.calls += 1
        return self.calls <= 8

    async def list_documents(self) -> dict:
        """List all published policy metadata. Summaries select documents, not answer evidence."""
        if not self.admit():
            return {"error": "tool_limit"}
        async with self.pool.acquire(timeout=3) as conn:
            rows = await conn.fetch("""SELECT DISTINCT ON (id) id,title,summary,keywords,revision
                FROM documents WHERE published ORDER BY id,revision DESC""")
        documents = [
            {**dict(row), "keywords": json.loads(row["keywords"])} for row in rows
        ]
        if len(documents) > 20 or len(json.dumps(documents)) > 6000:
            return {"error": "catalogue_limit"}
        self.listed.update((doc["id"], doc["revision"]) for doc in documents)
        return {"documents": documents}

    async def read_document(self, document_id: str, revision: int) -> dict:
        """Read the entire published policy at a revision returned by list_documents."""
        if not self.admit():
            return {"error": "tool_limit"}
        if (document_id, revision) not in self.listed:
            return {
                "error": "not_listed",
                "message": "List documents before reading a listed revision.",
            }
        async with self.pool.acquire(timeout=3) as conn:
            row = await conn.fetchrow(
                "SELECT id,revision,title,body FROM documents WHERE id=$1 AND revision=$2 AND published",
                document_id,
                revision,
            )
        if not row:
            return {"error": "missing_evidence"}
        key = (document_id, revision)
        if (
            len(row["body"]) > 6000
            or self.characters + len(row["body"]) > 24000
            or (key not in self.sources and len(self.sources) >= 4)
        ):
            return {"error": "evidence_limit"}
        self.characters += len(row["body"])
        source = {
            "id": document_id,
            "revision": revision,
            "title": row["title"],
            "url": f"/api/sources/{document_id}/{revision}",
        }
        self.sources[key] = source
        return {**source, "body": row["body"]}

    async def get_villa(self, villa_id: str) -> dict:
        """Get public villa facts and bedding. Known IDs: forest-suite, garden-villa. Not availability."""
        if not self.admit():
            return {"error": "tool_limit"}
        villa = await inventory.get_villa(self.pool, villa_id)
        return {"villa": villa} if villa else {"error": "unknown_villa"}

    async def check_availability(
        self, check_in: str, check_out: str, guests: int
    ) -> dict:
        """Check every night for exact YYYY-MM-DD dates and total guests, including children and infants."""
        if not self.admit():
            return {"error": "tool_limit"}
        result = await inventory.check_availability(
            self.pool, check_in, check_out, guests
        )
        # Retain the latest successful search only. Invalid subsequent input clears prior cards.
        self.availability = result if "error" not in result else None
        return result
