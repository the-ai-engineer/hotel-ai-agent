import base64
import json
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from .limits import reserve, turn_budgets
from .schemas import Answer, context_answer


async def owned(connection, conversation_id, owner, lock=False):
    row = (
        await connection.execute(
            text(
                "SELECT id FROM conversations WHERE id=:id AND owner_id=:owner"
                + (" FOR UPDATE" if lock else "")
            ),
            {"id": conversation_id, "owner": owner},
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "not_found")


async def create_conversation(db, owner, settings):
    id = uuid4()
    async with db.transaction() as connection:
        await reserve(connection, settings, [("guest-conversations-day", str(owner), 86400, 100)])
        await connection.execute(
            text("INSERT INTO conversations(id,owner_id) VALUES(:id,:owner)"),
            {"id": id, "owner": owner},
        )
    return id


async def expire(connection, conversation_id):
    await connection.execute(
        text("""
        UPDATE turns SET state='interrupted',error_code='interrupted'
        WHERE conversation_id=:id AND state='running' AND deadline<=clock_timestamp()
    """),
        {"id": conversation_id},
    )


async def admit(db, conversation_id, owner, input, timeout, settings, ip):
    async with db.transaction() as connection:
        await owned(connection, conversation_id, owner, lock=True)
        await expire(connection, conversation_id)
        old = (
            (
                await connection.execute(
                    text("SELECT * FROM turns WHERE conversation_id=:id AND client_turn_id=:turn"),
                    {"id": conversation_id, "turn": input.client_turn_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if old:
            if old["message"] != input.message:
                raise HTTPException(409, "idempotency_conflict")
            if old["state"] == "running":
                raise HTTPException(
                    409,
                    {
                        "code": "turn_running",
                        "status_url": f"/api/conversations/{conversation_id}/turns/{input.client_turn_id}",
                    },
                )
            return dict(old), False
        active = (
            await connection.execute(
                text("SELECT 1 FROM turns WHERE conversation_id=:id AND state='running'"),
                {"id": conversation_id},
            )
        ).scalar_one_or_none()
        if active:
            raise HTTPException(409, "conversation_busy")
        await reserve(connection, settings, turn_budgets(settings, owner, ip))
        row = (
            (
                await connection.execute(
                    text("""
            INSERT INTO turns(conversation_id,client_turn_id,message,deadline)
            VALUES(:id,:turn,:message,clock_timestamp()+make_interval(secs=>:timeout)) RETURNING *
        """),
                    {
                        "id": conversation_id,
                        "turn": input.client_turn_id,
                        "message": input.message,
                        "timeout": timeout,
                    },
                )
            )
            .mappings()
            .one()
        )
        return dict(row), True


async def finish(db, conversation_id, turn_id, state, result=None, error=None):
    if result is not None:
        result = Answer.model_validate(result).model_dump(mode="json")
        if len(json.dumps(result).encode()) > 65536:
            raise ValueError("Result too large")
    async with db.transaction() as connection:
        await connection.execute(
            text("SELECT id FROM conversations WHERE id=:id FOR UPDATE"), {"id": conversation_id}
        )
        row = (
            await connection.execute(
                text("""
            UPDATE turns SET state=:state,result=CAST(:result AS jsonb),error_code=:error
            WHERE conversation_id=:id AND client_turn_id=:turn AND state='running'
              AND deadline>clock_timestamp() RETURNING client_turn_id
        """),
                {
                    "id": conversation_id,
                    "turn": turn_id,
                    "state": state,
                    "result": json.dumps(result) if result else None,
                    "error": error,
                },
            )
        ).first()
        return row is not None


def decode_cursor(cursor):
    try:
        if len(cursor) > 256:
            raise ValueError("Cursor too long")
        timestamp, id = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        when = datetime.fromisoformat(timestamp)
        if when.tzinfo is None:
            raise ValueError("Cursor timezone missing")
        return {"before_time": when, "before_turn": UUID(id)}
    except (ValueError, TypeError, KeyError) as error:
        raise HTTPException(400, "invalid_cursor") from error


async def history_page(db, conversation_id, owner, before=None):
    cursor = decode_cursor(before) if before else {}
    condition = " AND (created_at,client_turn_id)<(:before_time,:before_turn)" if cursor else ""
    async with db.transaction() as connection:
        await owned(connection, conversation_id, owner, lock=True)
        await expire(connection, conversation_id)
        rows = (
            (
                await connection.execute(
                    text(
                        "SELECT * FROM turns WHERE conversation_id=:id"
                        + condition
                        + " ORDER BY created_at DESC,client_turn_id DESC LIMIT 51"
                    ),
                    {"id": conversation_id, **cursor},
                )
            )
            .mappings()
            .all()
        )
    page = [dict(row) for row in rows[:50]]
    next_cursor = None
    if len(rows) > 50:
        oldest = page[-1]
        next_cursor = base64.urlsafe_b64encode(
            json.dumps([oldest["created_at"].isoformat(), str(oldest["client_turn_id"])]).encode()
        ).decode()
    return {"turns": list(reversed(page)), "next_cursor": next_cursor}


async def history(db, conversation_id, owner):
    return (await history_page(db, conversation_id, owner))["turns"]


def context(rows):
    selected, size = [], 0
    for row in reversed(rows):
        if row["state"] != "completed":
            continue
        length = len(row["message"]) + len(context_answer(row["result"]))
        if size + length > 16000 or len(selected) == 20:
            break
        selected.append(row)
        size += length
    return list(reversed(selected))


async def status(db, conversation_id, owner, turn_id):
    async with db.transaction() as connection:
        await owned(connection, conversation_id, owner, lock=True)
        await expire(connection, conversation_id)
        row = (
            (
                await connection.execute(
                    text("SELECT * FROM turns WHERE conversation_id=:id AND client_turn_id=:turn"),
                    {"id": conversation_id, "turn": turn_id},
                )
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(404, "not_found")
    return dict(row)
