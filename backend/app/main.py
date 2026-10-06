import asyncio
import json
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

import anyio
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agent import answer
from app.db import connect, token_hash
from app.inventory import get_villa
from app.settings import Settings

log = logging.getLogger("hotel")


class Question(BaseModel):
    turn_id: UUID
    message: str = Field(min_length=1, max_length=2000)


def event(name, data):
    return f"event: {name}\ndata: {json.dumps(data)}\n\n"


def create_app(settings=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        app.state.pool = await connect(settings)
        app.state.answer = answer
        try:
            yield
        finally:
            await app.state.pool.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)

    def check_origin(request):
        if request.headers.get("origin") != settings.public_origin:
            raise HTTPException(403, "Untrusted origin")

    async def owner(request):
        token = request.cookies.get("hotel_session")
        if not token or len(token) > 128:
            raise HTTPException(401, "Start a new guest session")
        key = token_hash(token)
        async with app.state.pool.acquire(timeout=3) as conn:
            valid = await conn.fetchval(
                "SELECT 1 FROM guest_sessions WHERE token_hash=$1 AND expires_at>now()",
                key,
            )
        if not valid:
            raise HTTPException(401, "Guest session expired")
        return key

    @app.get("/api/health")
    async def health():
        try:
            async with app.state.pool.acquire(timeout=3) as conn:
                await conn.fetchval("SELECT 1 FROM documents LIMIT 1")
        except Exception:
            raise HTTPException(503, "Database unavailable") from None
        return {"status": "ok"}

    @app.post("/api/session")
    async def session(request: Request, response: Response):
        check_origin(request)
        try:
            await owner(request)
            return {"status": "ready"}
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
        token = secrets.token_urlsafe(32)
        async with app.state.pool.acquire(timeout=3) as conn:
            await conn.execute(
                "INSERT INTO guest_sessions(token_hash) VALUES ($1)", token_hash(token)
            )
        response.set_cookie(
            "hotel_session",
            token,
            max_age=86400,
            httponly=True,
            secure=settings.secure_cookie,
            samesite="lax",
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return {"status": "ready"}

    @app.post("/api/conversation")
    async def new_conversation(request: Request, response: Response):
        check_origin(request)
        key = await owner(request)
        async with app.state.pool.acquire(timeout=3) as conn:
            conversation = await conn.fetchval(
                """UPDATE guest_sessions SET conversation_id=gen_random_uuid(),active_turn=NULL,busy_until=NULL
                WHERE token_hash=$1 AND (busy_until IS NULL OR busy_until<now()) RETURNING conversation_id""",
                key,
            )
        if not conversation:
            raise HTTPException(
                409, "Stop the current answer before starting a new conversation"
            )
        response.headers["Cache-Control"] = "no-store"
        return {"status": "ready"}

    @app.get("/api/history")
    async def history(request: Request, response: Response):
        key = await owner(request)
        async with app.state.pool.acquire(timeout=3) as conn:
            rows = await conn.fetch(
                """SELECT question,answer,sources,availability FROM (
                SELECT question,answer,sources,availability,created_at FROM turns
                WHERE session_hash=$1 AND conversation_id=(SELECT conversation_id FROM guest_sessions WHERE token_hash=$1) AND status='completed' ORDER BY created_at DESC LIMIT 20
            ) recent ORDER BY created_at""",
                key,
            )
        response.headers["Cache-Control"] = "no-store"
        return {
            "turns": [
                {
                    **dict(row),
                    "sources": json.loads(row["sources"]),
                    "availability": json.loads(row["availability"])
                    if row["availability"]
                    else None,
                }
                for row in rows
            ]
        }

    @app.get("/api/sources/{document_id}/{revision}", response_class=PlainTextResponse)
    async def source(document_id: str, revision: int):
        async with app.state.pool.acquire(timeout=3) as conn:
            body = await conn.fetchval(
                "SELECT body FROM documents WHERE id=$1 AND revision=$2 AND published",
                document_id,
                revision,
            )
        if body is None:
            raise HTTPException(404, "Published source not found")
        return PlainTextResponse(
            body,
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )

    @app.post("/api/chat")
    async def chat(request: Request, question: Question):
        check_origin(request)
        key = await owner(request)
        if not question.message.strip():
            raise HTTPException(422, "Enter a question")
        deadline = asyncio.get_running_loop().time() + 90
        async with app.state.pool.acquire(timeout=3) as conn, conn.transaction():
            acquired = await conn.fetchval(
                """UPDATE guest_sessions SET active_turn=$2,busy_until=now()+interval '90 seconds'
                WHERE token_hash=$1 AND (busy_until IS NULL OR busy_until<now()) RETURNING conversation_id""",
                key,
                question.turn_id,
            )
            if not acquired:
                raise HTTPException(
                    409, "An answer is already running. Wait or stop it."
                )
            duplicate = await conn.fetchval(
                "SELECT 1 FROM turns WHERE id=$1", question.turn_id
            )
            if duplicate:
                raise HTTPException(409, "This question was already submitted")
            await conn.execute(
                "INSERT INTO turns(id,session_hash,question,status,conversation_id) VALUES ($1,$2,$3,$4,$5)",
                question.turn_id,
                key,
                question.message,
                "running",
                acquired,
            )
            rows = await conn.fetch(
                """SELECT question,answer FROM turns WHERE session_hash=$1 AND conversation_id=(SELECT conversation_id FROM guest_sessions WHERE token_hash=$1) AND status='completed'
                ORDER BY created_at DESC LIMIT 20""",
                key,
            )
        context = []
        size = 0
        for row in rows:
            length = len(row["question"]) + len(row["answer"])
            if size + length > 16000:
                break
            size += length
            context.append(dict(row))
        context.reverse()

        async def release(status):
            async with app.state.pool.acquire(timeout=3) as conn, conn.transaction():
                await conn.execute(
                    "UPDATE turns SET status=$2 WHERE id=$1 AND status='running'",
                    question.turn_id,
                    status,
                )
                await conn.execute(
                    "UPDATE guest_sessions SET active_turn=NULL,busy_until=NULL WHERE token_hash=$1 AND active_turn=$2",
                    key,
                    question.turn_id,
                )

        completed = False
        failure_status = "interrupted"

        async def stream():
            nonlocal completed, failure_status
            try:
                yield event("turn_started", {"turn_id": str(question.turn_id)})
                async with asyncio.timeout_at(deadline):
                    final = None
                    async for item in app.state.answer(
                        app.state.pool, settings, context, question.message
                    ):
                        if item["type"] == "text":
                            yield event("text", {"text": item["text"]})
                        elif item["type"] == "result":
                            final = {k: v for k, v in item.items() if k != "type"}
                    if not final or len(json.dumps(final).encode()) > 65536:
                        raise RuntimeError("Invalid final answer")
                    async with (
                        app.state.pool.acquire(timeout=3) as conn,
                        conn.transaction(),
                    ):
                        valid = await conn.fetchval(
                            "SELECT 1 FROM guest_sessions WHERE token_hash=$1 AND active_turn=$2 AND busy_until>now() FOR UPDATE",
                            key,
                            question.turn_id,
                        )
                        if not valid:
                            raise RuntimeError("Turn expired")
                        await conn.execute(
                            "UPDATE turns SET answer=$2,sources=$3::jsonb,availability=$4::jsonb,status='completed' WHERE id=$1 AND status='running'",
                            question.turn_id,
                            final["answer"],
                            json.dumps(final["sources"]),
                            json.dumps(final.get("availability")),
                        )
                        await conn.execute(
                            "UPDATE guest_sessions SET active_turn=NULL,busy_until=NULL WHERE token_hash=$1 AND active_turn=$2",
                            key,
                            question.turn_id,
                        )
                    completed = True
                    yield event("result", final)
                    yield event("done", {})
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                failure_status = "failed"
                log.warning(
                    "turn_failed turn_id=%s error_type=%s",
                    question.turn_id,
                    type(exc).__name__,
                )
                yield event(
                    "error",
                    {"message": "We could not complete that answer. Please try again."},
                )

        class GuestResponse(StreamingResponse):
            async def __call__(self, scope, receive, send):
                try:
                    await super().__call__(scope, receive, send)
                finally:
                    # Also release admission if disconnect happens before stream() starts.
                    if not completed:
                        try:
                            with anyio.CancelScope(shield=True), anyio.fail_after(4):
                                await release(failure_status)
                        except Exception:
                            log.warning(
                                "turn_cleanup_failed turn_id=%s", question.turn_id
                            )

        return GuestResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/villas/{villa_id}")
    async def villa_details(villa_id: str):
        villa = await get_villa(app.state.pool, villa_id)
        if not villa:
            raise HTTPException(404, "Villa not found")
        return villa

    @app.get("/villas/{villa_id}")
    async def villa_page(villa_id: str):
        if not await get_villa(app.state.pool, villa_id):
            raise HTTPException(404, "Villa not found")
        return FileResponse(Path(__file__).resolve().parents[2] / "frontend/villa.html")

    app.mount(
        "/",
        StaticFiles(
            directory=Path(__file__).resolve().parents[2] / "frontend", html=True
        ),
    )
    return app


app = create_app()
