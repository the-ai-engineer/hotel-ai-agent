import json

from fastapi import HTTPException

from app.db import token_hash


class ModelAdmission:
    """One event-loop process: taking a slot never waits or yields."""

    def __init__(self, limit):
        self.limit = limit
        self.active = 0

    def take(self):
        if self.active >= self.limit:
            raise HTTPException(
                429,
                "The concierge is busy. Please try again shortly.",
                headers={"Retry-After": "5"},
            )
        self.active += 1

    def release(self):
        self.active -= 1


def ip_key(request):
    # Ignore forwarded headers until the deployment proxy chain is verified.
    return token_hash(request.client.host if request.client else "unknown")


async def budget(conn, limits):
    """Charge all budgets atomically in the caller's transaction."""
    # Bounded opportunistic cleanup; scheduled retention remains GRA-217.
    await conn.execute("""WITH expired AS (
        SELECT scope,bucket FROM rate_counters WHERE expires_at<=now()
        LIMIT 1000 FOR UPDATE SKIP LOCKED
    ) DELETE FROM rate_counters r USING expired e WHERE r.scope=e.scope AND r.bucket=e.bucket""")
    for scope, limit, daily in sorted(limits):
        used = await conn.fetchval(
            """INSERT INTO rate_counters(scope,bucket,used,expires_at)
            VALUES ($1, CASE WHEN $3 THEN
              date_trunc('day',now() AT TIME ZONE 'Asia/Makassar') AT TIME ZONE 'Asia/Makassar'
              ELSE date_trunc('minute',now()) END, 1,
              now()+CASE WHEN $3 THEN interval '2 days' ELSE interval '2 minutes' END)
            ON CONFLICT(scope,bucket) DO UPDATE SET used=rate_counters.used+1
            WHERE rate_counters.used<$2 RETURNING used""",
            scope,
            limit,
            daily,
        )
        if used is None:
            raise HTTPException(
                429,
                "The concierge request limit was reached. Please try again later.",
                headers={"Retry-After": "60"},
            )


async def expire(conn, key):
    # All callers lock the session first. A crash is recovered by the deadline.
    await conn.execute(
        """UPDATE turns SET status='interrupted' WHERE session_hash=$1
        AND status='running' AND deadline_at<=now()""",
        key,
    )
    await conn.execute(
        """UPDATE guest_sessions SET active_turn=NULL,busy_until=NULL
        WHERE token_hash=$1 AND busy_until<=now()""",
        key,
    )


async def locked_session(conn, key):
    row = await conn.fetchrow(
        "SELECT * FROM guest_sessions WHERE token_hash=$1 AND expires_at>now() FOR UPDATE",
        key,
    )
    if row is None:
        raise HTTPException(401, "Guest session expired")
    await expire(conn, key)
    return await conn.fetchrow("SELECT * FROM guest_sessions WHERE token_hash=$1", key)


async def status(conn, key, turn_id, conversation_id):
    row = await conn.fetchrow(
        """SELECT t.*,
        (SELECT json_build_object('id',r.id,'reference',b.reference,'note',r.note,'status',r.status)
        FROM hotel_requests r JOIN bookings b ON b.id=r.booking_id WHERE r.id=t.request_id) AS hotel_request
        FROM turns t WHERE t.id=$1 AND t.session_hash=$2 AND t.conversation_id=$3""",
        turn_id,
        key,
        conversation_id,
    )
    if row is None:
        raise HTTPException(404, "Turn not found")
    data = {
        "turn_id": str(turn_id),
        "status": row["status"],
        "status_url": f"/api/turns/{turn_id}",
        "question": row["question"],
    }
    if row["status"] == "completed":
        data["result"] = {
            "answer": row["answer"],
            "sources": json.loads(row["sources"]),
            "availability": json.loads(row["availability"])
            if row["availability"]
            else None,
            "hotel_request": json.loads(row["hotel_request"])
            if row["hotel_request"]
            else None,
        }
    return data


async def interrupt(pool, key, turn_id, outcome="interrupted"):
    async with pool.acquire(timeout=3) as conn, conn.transaction():
        await locked_session(conn, key)
        await conn.execute(
            "UPDATE turns SET status=$3 WHERE id=$1 AND session_hash=$2 AND status='running'",
            turn_id,
            key,
            outcome,
        )
        await conn.execute(
            "UPDATE guest_sessions SET active_turn=NULL,busy_until=NULL WHERE token_hash=$1 AND active_turn=$2",
            key,
            turn_id,
        )
