import hashlib
import secrets
from uuid import UUID, uuid4

from fastapi import HTTPException, Request, Response
from sqlalchemy import text

from .limits import ip_key, reserve

COOKIE = "hotel_session"


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def session_owner(request: Request) -> UUID:
    token = request.cookies.get(COOKIE, "")
    if not token or len(token) > 100:
        raise HTTPException(401, "session_expired")
    async with request.app.state.db.transaction() as connection:
        owner = (
            await connection.execute(
                text(
                    "SELECT id FROM guest_sessions WHERE token_hash=:token AND expires_at>clock_timestamp()"
                ),
                {"token": token_hash(token)},
            )
        ).scalar_one_or_none()
    if owner is None:
        raise HTTPException(401, "session_expired")
    return owner


async def ensure_session(request: Request, response: Response) -> dict:
    try:
        owner = await session_owner(request)
        return {"session_id": str(owner)}
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
    owner, token = uuid4(), secrets.token_urlsafe(32)
    async with request.app.state.db.transaction() as connection:
        settings = request.app.state.settings
        await reserve(
            connection,
            settings,
            [("session-ip-minute", ip_key(request), 60, settings.demo_ip_limit_override or 10)],
        )
        await connection.execute(
            text("INSERT INTO guest_sessions(id,token_hash) VALUES(:id,:token)"),
            {"id": owner, "token": token_hash(token)},
        )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=request.app.state.settings.app_env != "local",
        samesite="lax",
        max_age=86400,
        path="/",
    )
    return {"session_id": str(owner)}
