"""Guest-owned demo reservations and explicitly confirmed hotel requests."""

import json
import secrets
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.inventory import availability_on_connection


class ReservationError(Exception):
    pass


def property_today():
    return datetime.now(ZoneInfo("Asia/Makassar")).date()


def booking_data(row):
    return {
        "reference": row["reference"],
        "villa_id": row["villa_id"],
        "villa_name": json.loads(row["data"])["name"],
        "check_in": row["check_in"].isoformat(),
        "check_out": row["check_out"].isoformat(),
        "guests": row["guests"],
        "status": row["status"],
    }


async def lookup_booking(pool, owner, reference=""):
    async with pool.acquire(timeout=3) as conn:
        row = await conn.fetchrow(
            """SELECT b.*,v.data FROM bookings b JOIN villas v ON v.id=b.villa_id
            WHERE b.session_hash=$1 AND ($2='' OR b.reference=$2)
            ORDER BY b.created_at DESC,b.id DESC LIMIT 1""",
            owner,
            reference.strip().upper(),
        )
    return booking_data(row) if row else None


async def reserve(pool, owner, request_id, villa_id, check_in, check_out, guests):
    async with pool.acquire(timeout=3) as conn, conn.transaction():
        # Same request and same villa serialize across all app instances.
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
            f"booking:{request_id}",
        )
        existing = await conn.fetchrow(
            "SELECT b.*,v.data FROM bookings b JOIN villas v ON v.id=b.villa_id WHERE request_id=$1",
            request_id,
        )
        if existing:
            if (
                existing["session_hash"] != owner
                or existing["villa_id"] != villa_id
                or existing["check_in"].isoformat() != check_in
                or existing["check_out"].isoformat() != check_out
                or existing["guests"] != guests
            ):
                raise ReservationError(
                    "This confirmation does not match the reservation. Review your details again."
                )
            return booking_data(existing)
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1,0))", f"villa:{villa_id}"
        )
        availability = await availability_on_connection(
            conn, check_in, check_out, guests
        )
        if "error" in availability:
            raise ReservationError(availability["message"])
        if date.fromisoformat(check_in) < property_today():
            raise ReservationError("Choose a check-in date that is today or later.")
        if not any(v["id"] == villa_id for v in availability["cards"]):
            raise ReservationError(
                "This villa is no longer available for the whole stay. Check another villa or dates."
            )
        reference = "SH-" + secrets.token_hex(6).upper()
        await conn.execute(
            """INSERT INTO bookings(villa_id,check_in,check_out,status,reference,request_id,session_hash,guests)
            VALUES($1,$2,$3,'confirmed',$4,$5,$6,$7)""",
            villa_id,
            date.fromisoformat(check_in),
            date.fromisoformat(check_out),
            reference,
            request_id,
            owner,
            guests,
        )
        row = await conn.fetchrow(
            "SELECT b.*,v.data FROM bookings b JOIN villas v ON v.id=b.villa_id WHERE reference=$1",
            reference,
        )
        return booking_data(row)


async def prepare_request(pool, guest, reference, note):
    note = note.strip()
    if not 1 <= len(note) <= 1000:
        return {
            "error": "invalid_note",
            "message": "Provide a note of 1–1000 characters.",
        }
    async with pool.acquire(timeout=3) as conn:
        booking = await conn.fetchval(
            "SELECT id FROM bookings WHERE reference=$1 AND session_hash=$2",
            reference.strip().upper(),
            guest["session_hash"],
        )
        if not booking:
            return {
                "error": "booking_not_found",
                "message": "No matching booking in this guest session.",
            }
    return {
        "id": str(uuid.uuid4()),
        "reference": reference.strip().upper(),
        "note": note,
        "status": "draft",
    }


async def save_request(conn, owner, conversation_id, proposed):
    # Persist only alongside a completed answer, never for a stopped model run.
    await conn.execute(
        "UPDATE hotel_requests SET status='superseded' WHERE conversation_id=$1 AND status='draft'",
        conversation_id,
    )
    saved = await conn.fetchval(
        """INSERT INTO hotel_requests(id,booking_id,conversation_id,note)
        SELECT $1,id,$2,$3 FROM bookings WHERE reference=$4 AND session_hash=$5 RETURNING hotel_requests.id""",
        uuid.UUID(proposed["id"]),
        conversation_id,
        proposed["note"],
        proposed["reference"],
        owner,
    )
    if not saved:
        raise ReservationError("No matching booking in this guest session.")


async def confirm_request(pool, owner, request_id):
    async with pool.acquire(timeout=3) as conn, conn.transaction():
        conversation_id = await conn.fetchval(
            "SELECT conversation_id FROM guest_sessions WHERE token_hash=$1 FOR UPDATE",
            owner,
        )
        row = await conn.fetchrow(
            """SELECT r.*,b.reference FROM hotel_requests r JOIN bookings b ON b.id=r.booking_id
            WHERE r.id=$1 AND b.session_hash=$2 AND r.conversation_id=$3
            AND EXISTS (SELECT 1 FROM turns t WHERE t.request_id=r.id AND t.status='completed')
            FOR UPDATE OF r""",
            request_id,
            owner,
            conversation_id,
        )
        if not row or row["status"] == "superseded":
            raise ReservationError(
                "This request is unavailable in your current conversation."
            )
        if row["status"] == "draft":
            valid = await conn.fetchval(
                "SELECT expires_at>now() FROM hotel_requests WHERE id=$1", request_id
            )
            if not valid:
                raise ReservationError(
                    "This request expired. Ask the concierge to prepare it again."
                )
            await conn.execute(
                "UPDATE hotel_requests SET status='pending_review' WHERE id=$1",
                request_id,
            )
        return {
            "id": str(request_id),
            "reference": row["reference"],
            "note": row["note"],
            "status": "pending_review",
        }
