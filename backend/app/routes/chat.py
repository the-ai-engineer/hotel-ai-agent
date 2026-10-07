import asyncio
import json
from contextlib import aclosing, suppress
from datetime import UTC, datetime
from uuid import UUID

import anyio
from fastapi import APIRouter, Depends, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from .. import sessions, turns
from ..schemas import TurnInput

router = APIRouter(prefix="/api")


def sse(event, data):
    return f"event: {event}\ndata: {json.dumps(jsonable_encoder(data))}\n\n"


@router.post("/session")
async def session(request: Request, response: Response):
    return await sessions.ensure_session(request, response)


@router.post("/conversations")
async def new_conversation(request: Request, owner=Depends(sessions.session_owner)):
    id = await turns.create_conversation(request.app.state.db, owner)
    return {"id": str(id)}


@router.get("/conversations/{conversation_id}")
async def conversation(
    conversation_id: UUID, request: Request, owner=Depends(sessions.session_owner)
):
    return {
        "id": str(conversation_id),
        "turns": await turns.history(request.app.state.db, conversation_id, owner),
    }


@router.get("/conversations/{conversation_id}/turns/{turn_id}")
async def turn_status(
    conversation_id: UUID, turn_id: UUID, request: Request, owner=Depends(sessions.session_owner)
):
    return await turns.status(request.app.state.db, conversation_id, owner, turn_id)


@router.post("/conversations/{conversation_id}/turns")
async def question(
    conversation_id: UUID, input: TurnInput, request: Request, owner=Depends(sessions.session_owner)
):
    db = request.app.state.db
    record, fresh = await turns.admit(
        db, conversation_id, owner, input, request.app.state.settings.turn_timeout_seconds
    )
    status_url = f"/api/conversations/{conversation_id}/turns/{input.client_turn_id}"

    async def stream():
        try:
            yield sse(
                "turn_started", {"turn_id": str(input.client_turn_id), "status_url": status_url}
            )
            if not fresh:
                if record["state"] == "completed":
                    yield sse("result", record["result"])
                    yield sse("done", {"turn_id": str(input.client_turn_id)})
                else:
                    yield sse(
                        "error",
                        {
                            "code": record["error_code"],
                            "message": "That attempt did not complete.",
                            "request_id": request.state.request_id,
                        },
                    )
                return
            history = turns.context(await turns.history(db, conversation_id, owner))
            result = None
            async with asyncio.timeout(
                max(0, (record["deadline"] - datetime.now(UTC)).total_seconds())
            ):
                async with aclosing(
                    request.app.state.concierge.run(input.client_turn_id, input.message, history)
                ) as events:
                    async for event in events:
                        if event["event"] == "answer":
                            result = event["data"]
                        else:
                            yield sse(event["event"], event["data"])
                if result is None or not await turns.finish(
                    db, conversation_id, input.client_turn_id, "completed", result
                ):
                    raise RuntimeError("Unable to commit answer")
            yield sse("result", result)
            yield sse("done", {"turn_id": str(input.client_turn_id)})
        except asyncio.CancelledError:
            raise
        except Exception:
            with anyio.move_on_after(3, shield=True), suppress(Exception):
                await turns.finish(
                    db, conversation_id, input.client_turn_id, "failed", error="unavailable"
                )
            yield sse(
                "error",
                {
                    "code": "unavailable",
                    "message": "We couldn't complete that request. Please try again or contact the hotel.",
                    "request_id": request.state.request_id,
                },
            )
        finally:
            if fresh:
                with anyio.move_on_after(3, shield=True), suppress(Exception):
                    await turns.finish(
                        db,
                        conversation_id,
                        input.client_turn_id,
                        "interrupted",
                        error="interrupted",
                    )

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"}
    )
