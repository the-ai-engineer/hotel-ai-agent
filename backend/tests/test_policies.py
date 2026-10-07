import shutil
from pathlib import Path

import pytest

from app.seed import import_policies
from app.tools import HotelTools

SOURCE = Path(__file__).resolve().parents[2] / "hotel"


async def test_catalogue_body_and_budget(pool):
    tools = HotelTools(pool)
    assert (await tools.read_document("dining-policy", 2))["error"] == "not_listed"
    catalogue = (await tools.list_documents())["documents"]
    assert len(catalogue) == 7
    assert all("body" not in row and "file" not in row for row in catalogue)
    doc = await tools.read_document("dining-policy", 2)
    assert doc["body"] == (SOURCE / "policies/dining.md").read_text()
    assert doc["url"] == "/api/sources/dining-policy/2"
    assert len(tools.sources) == 1
    for _ in range(6):
        await tools.read_document("dining-policy", 2)
    assert (await tools.list_documents())["error"] == "tool_limit"


async def test_atomic_import_pins_and_withdrawal(pool, tmp_path):
    shutil.copytree(SOURCE, tmp_path / "hotel")
    source = tmp_path / "hotel"
    tools = HotelTools(pool)
    await tools.list_documents()
    path = source / "policies/dining.md"
    original = path.read_text()
    path.write_text(
        original.replace("Revision: 2", "Revision: 3").replace("10:30", "11:00")
    )
    await import_policies(pool, source)
    assert "10:30" in (await tools.read_document("dining-policy", 2))["body"]
    new = HotelTools(pool)
    assert (
        next(
            d
            for d in (await new.list_documents())["documents"]
            if d["id"] == "dining-policy"
        )["revision"]
        == 3
    )
    assert "11:00" in (await new.read_document("dining-policy", 3))["body"]
    path.write_text(
        path.read_text()
        .replace("Revision: 3", "Revision: 4")
        .replace("Status: published", "Status: unpublished")
    )
    await import_policies(pool, source)
    assert (await tools.read_document("dining-policy", 2))[
        "error"
    ] == "missing_evidence"
    assert "dining-policy" not in [
        d["id"] for d in (await HotelTools(pool).list_documents())["documents"]
    ]


async def test_reject_oversized_and_changed_revision_without_partial_import(
    pool, tmp_path
):
    shutil.copytree(SOURCE, tmp_path / "hotel")
    source = tmp_path / "hotel"
    path = source / "policies/dining.md"
    original = path.read_text()
    path.write_text(original + "x" * 6000)
    with pytest.raises(ValueError, match="6000"):
        await import_policies(pool, source)
    path.write_text(original.replace("10:30", "11:00"))
    with pytest.raises(ValueError, match="increment revision"):
        await import_policies(pool, source)
    async with pool.acquire() as conn:
        assert await conn.fetchval("SELECT count(*) FROM documents") == 7
        assert "10:30" in await conn.fetchval(
            "SELECT body FROM documents WHERE id='dining-policy'"
        )


async def test_four_complete_documents_not_truncated(pool):
    tools = HotelTools(pool)
    catalogue = (await tools.list_documents())["documents"]
    for doc in catalogue[:4]:
        result = await tools.read_document(doc["id"], doc["revision"])
        assert result["body"].startswith("# ")
    assert (await tools.read_document(catalogue[4]["id"], catalogue[4]["revision"]))[
        "error"
    ] == "evidence_limit"


async def test_missing_id_is_not_exposed(pool):
    tools = HotelTools(pool)
    await tools.list_documents()
    assert (await tools.read_document("private-staff", 1))["error"] == "not_listed"
