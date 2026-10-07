from sqlalchemy import text

from .schemas import Source


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
