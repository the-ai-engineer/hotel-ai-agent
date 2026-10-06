import hashlib
import hmac
import ipaddress

from fastapi import HTTPException
from sqlalchemy import text


def ip_key(request):
    # Never trust arbitrary forwarding headers. A verified ingress adapter is a public-release gate.
    value = request.client.host if request.client else "unknown"
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return "unknown"


async def reserve(connection, settings, scopes):
    now = float(
        (
            await connection.execute(text("SELECT extract(epoch FROM clock_timestamp())"))
        ).scalar_one()
    )
    for scope, key, seconds, maximum in sorted(scopes):
        start = int(now // seconds) * seconds
        key_hash = hmac.new(
            settings.ip_hash_secret.get_secret_value().encode(),
            f"{scope}:{key}".encode(),
            hashlib.sha256,
        ).hexdigest()
        admitted = (
            await connection.execute(
                text("""
            INSERT INTO rate_buckets(scope,key_hash,window_start,admitted,expires_at)
            VALUES(:scope,:key,:start,1,to_timestamp(:expires))
            ON CONFLICT(scope,key_hash,window_start) DO UPDATE
            SET admitted=rate_buckets.admitted+1 WHERE rate_buckets.admitted<:maximum
            RETURNING admitted
        """),
                {
                    "scope": scope,
                    "key": key_hash,
                    "start": start,
                    "expires": start + seconds,
                    "maximum": maximum,
                },
            )
        ).scalar_one_or_none()
        if admitted is None:
            raise HTTPException(
                429,
                "budget_exhausted",
                headers={"Retry-After": str(max(1, int(start + seconds - now) + 1))},
            )


def turn_budgets(settings, owner, ip):
    return [
        ("property-minute", "hotel", 60, settings.property_limit),
        ("property-day", "hotel", 86400, 10000),
        ("guest-minute", str(owner), 60, 10),
        ("ip-minute", ip, 60, settings.demo_ip_limit_override or 30),
    ]
