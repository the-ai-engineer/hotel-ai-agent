from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from .agent import Concierge
from .boundary import Boundary
from .config import Settings
from .db import Database
from .routes import chat, health, policies


def create_app(settings=None, db=None, model=None):
    settings = settings or Settings()
    database = db or Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        await database.ready()
        app.state.concierge = Concierge(settings, database, model)
        try:
            yield
        finally:
            await app.state.concierge.close()
            await database.close()

    app = FastAPI(lifespan=lifespan)
    app.state.settings, app.state.db = settings, database

    app.add_middleware(Boundary, settings=settings)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        body = {"code": exc.detail} if isinstance(exc.detail, str) else dict(exc.detail)
        return JSONResponse(
            {**body, "request_id": request.state.request_id},
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        return JSONResponse(
            {"code": "unavailable", "request_id": request.state.request_id}, status_code=503
        )

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse(
            {"code": "invalid_input", "request_id": request.state.request_id}, status_code=400
        )

    app.include_router(chat.router)
    app.include_router(policies.router)
    app.include_router(health.router)

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def missing_api(path: str):
        return JSONResponse({"code": "not_found"}, status_code=404)

    frontend = Path(__file__).resolve().parents[2] / "frontend"
    app.mount("/", StaticFiles(directory=frontend, html=True), name="site")
    return app
