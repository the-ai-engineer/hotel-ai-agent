import asyncio
import json
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

import anyio
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import reservations, turns
from app.agent import answer
from app.db import connect, token_hash
from app.inventory import check_availability, get_villa
from app.settings import Settings

log = logging.getLogger("hotel")


class ReservationInput(BaseModel):
    request_id: UUID
    villa_id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=80)
    check_in: str = Field(max_length=10)
    check_out: str = Field(max_length=10)
    guests: int = Field(ge=1, le=8, strict=True)


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
        app.state.model_admission = turns.ModelAdmission(settings.active_agent_limit)
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
        async with app.state.pool.acquire(timeout=3) as conn, conn.transaction():
            await turns.budget(
                conn,
                [
                    (
                        "session-ip:" + turns.ip_key(request),
                        settings.sessions_per_ip_minute,
                        False,
                    )
                ],
            )
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
        async with app.state.pool.acquire(timeout=3) as conn, conn.transaction():
            await turns.locked_session(conn, key)
            await turns.budget(
                conn,
                [
                    (
                        "conversation:" + key,
                        settings.conversations_per_session_minute,
                        False,
                    )
                ],
            )
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
        async with app.state.pool.acquire(timeout=3) as conn, conn.transaction():
            session = await turns.locked_session(conn, key)
            active = (
                await turns.status(
                    conn, key, session["active_turn"], session["conversation_id"]
                )
                if session["active_turn"]
                else None
            )
            last_id = await conn.fetchval(
                "SELECT id FROM turns WHERE session_hash=$1 AND conversation_id=$2 ORDER BY created_at DESC LIMIT 1",
                key,
                session["conversation_id"],
            )
            last_attempt = (
                await turns.status(conn, key, last_id, session["conversation_id"])
                if last_id
                else None
            )
            if last_attempt and last_attempt["status"] == "completed":
                last_attempt = None
            rows = await conn.fetch(
                """SELECT question,answer,sources,availability,
                (SELECT json_build_object('id',r.id,'reference',b.reference,'note',r.note,'status',r.status)
                FROM hotel_requests r JOIN bookings b ON b.id=r.booking_id WHERE r.id=recent.request_id) AS hotel_request FROM (
                SELECT question,answer,sources,availability,request_id,created_at FROM turns
                WHERE session_hash=$1 AND conversation_id=(SELECT conversation_id FROM guest_sessions WHERE token_hash=$1) AND status='completed' ORDER BY created_at DESC LIMIT 20
            ) recent ORDER BY created_at""",
                key,
            )
        response.headers["Cache-Control"] = "no-store"
        return {
            "active_turn": active,
            "last_attempt": last_attempt,
            "turns": [
                {
                    **dict(row),
                    "sources": json.loads(row["sources"]),
                    "hotel_request": json.loads(row["hotel_request"])
                    if row["hotel_request"]
                    else None,
                    "availability": json.loads(row["availability"])
                    if row["availability"]
                    else None,
                }
                for row in rows
            ],
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

    @app.get("/api/turns/{turn_id}")
    async def turn_status(turn_id: UUID, request: Request, response: Response):
        key = await owner(request)
        async with app.state.pool.acquire(timeout=3) as conn, conn.transaction():
            session = await turns.locked_session(conn, key)
            data = await turns.status(conn, key, turn_id, session["conversation_id"])
        response.headers["Cache-Control"] = "no-store"
        return data

    @app.post("/api/turns/{turn_id}/stop")
    async def stop_turn(turn_id: UUID, request: Request, response: Response):
        check_origin(request)
        key = await owner(request)
        async with app.state.pool.acquire(timeout=3) as conn, conn.transaction():
            session = await turns.locked_session(conn, key)
            await turns.status(conn, key, turn_id, session["conversation_id"])
            await conn.execute(
                "UPDATE turns SET status='interrupted' WHERE id=$1 AND status='running'",
                turn_id,
            )
            await conn.execute(
                "UPDATE guest_sessions SET active_turn=NULL,busy_until=NULL WHERE token_hash=$1 AND active_turn=$2",
                key,
                turn_id,
            )
            data = await turns.status(conn, key, turn_id, session["conversation_id"])
        response.headers["Cache-Control"] = "no-store"
        return data

    @app.post("/api/chat")
    async def chat(request: Request, question: Question):
        check_origin(request)
        key = await owner(request)
        if not question.message.strip():
            raise HTTPException(422, "Enter a question")
        slot = False
        try:
            async with app.state.pool.acquire(timeout=3) as conn, conn.transaction():
                session = await turns.locked_session(conn, key)
                existing = await conn.fetchrow(
                    "SELECT session_hash,conversation_id FROM turns WHERE id=$1",
                    question.turn_id,
                )
                if existing:
                    if (
                        existing["session_hash"] != key
                        or existing["conversation_id"] != session["conversation_id"]
                    ):
                        raise HTTPException(404, "Turn not found")
                    data = await turns.status(
                        conn, key, question.turn_id, session["conversation_id"]
                    )
                    return JSONResponse(
                        data,
                        status_code=202 if data["status"] == "running" else 200,
                        headers={"Cache-Control": "no-store"},
                    )
                if session["active_turn"]:
                    raise HTTPException(
                        409, "An answer is already running. Wait or stop it."
                    )
                app.state.model_admission.take()
                slot = True
                await turns.budget(
                    conn,
                    [
                        (
                            "turn-session:" + key,
                            settings.session_turns_per_minute,
                            False,
                        ),
                        (
                            "turn-ip:" + turns.ip_key(request),
                            settings.ip_turns_per_minute,
                            False,
                        ),
                        (
                            "turn-property-minute",
                            settings.property_turns_per_minute,
                            False,
                        ),
                        ("turn-property-day", settings.property_turns_per_day, True),
                    ],
                )
                acquired = session["conversation_id"]
                deadline_at = await conn.fetchval(
                    "UPDATE guest_sessions SET active_turn=$2,busy_until=now()+$3*interval '1 second' WHERE token_hash=$1 RETURNING busy_until",
                    key,
                    question.turn_id,
                    settings.turn_timeout_seconds,
                )
                inserted = await conn.fetchval(
                    "INSERT INTO turns(id,session_hash,question,status,conversation_id,deadline_at) VALUES ($1,$2,$3,'running',$4,$5) ON CONFLICT DO NOTHING RETURNING id",
                    question.turn_id,
                    key,
                    question.message,
                    acquired,
                    deadline_at,
                )
                if not inserted:
                    raise HTTPException(404, "Turn not found")
                rows = await conn.fetch(
                    "SELECT question,answer FROM turns WHERE session_hash=$1 AND conversation_id=$2 AND status='completed' ORDER BY created_at DESC LIMIT 20",
                    key,
                    acquired,
                )
        except BaseException:
            if slot:
                app.state.model_admission.release()
            raise
        context = []
        size = 0
        for row in rows:
            length = len(row["question"]) + len(row["answer"])
            if size + length > 16000:
                break
            size += length
            context.append(dict(row))
        context.reverse()
        completed = False
        failure_status = "interrupted"
        stopped_remotely = False

        async def watch_stop(task):
            nonlocal stopped_remotely, failure_status
            # Stop can reach another API process. Durable status is authoritative.
            try:
                while True:
                    await asyncio.sleep(0.25)
                    async with app.state.pool.acquire(timeout=3) as conn:
                        interrupted = await conn.fetchval(
                            "SELECT status IN ('interrupted','failed') OR (status='running' AND deadline_at<=now()) FROM turns WHERE id=$1",
                            question.turn_id,
                        )
                    if interrupted and not completed:
                        stopped_remotely = True
                        task.cancel()
                        return
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # If monitoring fails, stop model work rather than silently ignoring Stop.
                log.warning(
                    "turn_watch_failed turn_id=%s error_type=%s",
                    question.turn_id,
                    type(exc).__name__,
                )
                failure_status = "failed"
                stopped_remotely = True
                task.cancel()

        async def stream():
            nonlocal completed, failure_status
            watcher = None
            try:
                watcher = asyncio.create_task(
                    watch_stop(asyncio.current_task()), name="hotel-turn-watch"
                )
                yield event(
                    "turn_started",
                    {
                        "turn_id": str(question.turn_id),
                        "status_url": f"/api/turns/{question.turn_id}",
                    },
                )
                # Use the stored deadline, including admission time.
                from datetime import datetime, timezone

                remaining = max(
                    0, (deadline_at - datetime.now(timezone.utc)).total_seconds()
                )
                async with asyncio.timeout(remaining):
                    final = None
                    async for item in app.state.answer(
                        app.state.pool,
                        settings,
                        context,
                        question.message,
                        guest={"session_hash": key, "conversation_id": str(acquired)},
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
                        await turns.locked_session(conn, key)
                        valid = await conn.fetchval(
                            "SELECT 1 FROM guest_sessions s JOIN turns t ON t.id=s.active_turn WHERE s.token_hash=$1 AND s.active_turn=$2 AND s.conversation_id=$3 AND s.busy_until>now() AND t.status='running' AND t.deadline_at>now()",
                            key,
                            question.turn_id,
                            acquired,
                        )
                        if not valid:
                            raise RuntimeError("Turn expired")
                        if final.get("hotel_request"):
                            await reservations.save_request(
                                conn, key, acquired, final["hotel_request"]
                            )
                        await conn.execute(
                            "UPDATE turns SET answer=$2,sources=$3::jsonb,availability=$4::jsonb,request_id=$5,status='completed' WHERE id=$1 AND status='running'",
                            question.turn_id,
                            final["answer"],
                            json.dumps(final["sources"]),
                            json.dumps(final.get("availability")),
                            UUID(final["hotel_request"]["id"])
                            if final.get("hotel_request")
                            else None,
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
                if not stopped_remotely:
                    raise
                yield event(
                    "error",
                    {"message": "That answer was interrupted. You can ask again."},
                )
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
            finally:
                if watcher:
                    watcher.cancel()
                    await asyncio.gather(watcher, return_exceptions=True)

        class GuestResponse(StreamingResponse):
            async def __call__(self, scope, receive, send):
                try:
                    await super().__call__(scope, receive, send)
                finally:
                    try:
                        if not completed:
                            with anyio.CancelScope(shield=True), anyio.fail_after(7):
                                await turns.interrupt(
                                    app.state.pool,
                                    key,
                                    question.turn_id,
                                    failure_status,
                                )
                    except Exception:
                        log.warning("turn_cleanup_failed turn_id=%s", question.turn_id)
                    finally:
                        app.state.model_admission.release()

        return GuestResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/bookings")
    async def create_booking(
        request: Request, details: ReservationInput, response: Response
    ):
        check_origin(request)
        key = await owner(request)
        try:
            booking = await reservations.reserve(
                app.state.pool, key, **details.model_dump()
            )
        except reservations.ReservationError as exc:
            raise HTTPException(409, str(exc)) from None
        response.headers["Cache-Control"] = "no-store"
        return {"booking": booking}

    @app.get("/api/bookings/{reference}")
    async def get_booking(reference: str, request: Request, response: Response):
        key = await owner(request)
        booking = await reservations.lookup_booking(app.state.pool, key, reference)
        if not booking:
            raise HTTPException(404, "No matching booking in this guest session")
        response.headers["Cache-Control"] = "no-store"
        return {"booking": booking}

    @app.post("/api/requests/{request_id}/confirm")
    async def send_request(request_id: UUID, request: Request):
        check_origin(request)
        key = await owner(request)
        try:
            return await reservations.confirm_request(app.state.pool, key, request_id)
        except reservations.ReservationError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.get("/book")
    async def booking_page():
        return FileResponse(Path(__file__).resolve().parents[2] / "frontend/book.html")

    @app.get("/api/availability")
    async def availability(check_in: str, check_out: str, guests: int):
        return await check_availability(app.state.pool, check_in, check_out, guests)

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
