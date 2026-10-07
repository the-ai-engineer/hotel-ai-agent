from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..hotel import policy_page

router = APIRouter()
templates = Environment(
    loader=FileSystemLoader(Path(__file__).parents[1] / "templates"), autoescape=select_autoescape()
)


@router.get("/policies/{slug}", response_class=HTMLResponse)
async def policy(slug: str, request: Request, version: int | None = Query(default=None, ge=1)):
    rows = await policy_page(request.app.state.db, slug, version)
    if not rows:
        raise HTTPException(404, "not_found")
    return templates.get_template("policy.html").render(
        title=rows[0]["title"],
        version=rows[0]["version"],
        superseded=rows[0]["superseded"],
        passages=[r["body"] for r in rows],
    )
