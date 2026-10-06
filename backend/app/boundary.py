from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class Boundary:
    """Check browser mutation requests without buffering or wrapping SSE streams."""

    def __init__(self, app, settings):
        self.app, self.settings = app, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request = Request(scope)
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            code = None
            status = 400
            if request.headers.get("origin") not in self.settings.origins:
                code, status = "invalid_origin", 403
            elif request.headers.get("content-type", "").split(";")[0] != "application/json":
                code = "invalid_content_type"
            if code:
                return await JSONResponse(
                    {"code": code, "request_id": request_id}, status_code=status
                )(scope, receive, send)

        received = 0

        async def bounded_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > 32768:
                    raise HTTPException(413, "body_too_large")
            return message

        async def respond(message):
            if message["type"] == "http.response.start":
                message = {**message, "headers": list(message.get("headers", []))}
                message["headers"].append((b"x-request-id", request_id.encode()))
                if request.url.path.startswith("/api/"):
                    message["headers"].append((b"cache-control", b"no-store"))
            await send(message)

        await self.app(scope, bounded_receive, respond)
