import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.requests import Request
from starlette.responses import Response

from preflight_api.config import get_settings
from preflight_api.db import engine
from preflight_api.logging_config import configure_logging
from preflight_api.models import Base
from preflight_api.redis_client import close_redis
from preflight_api.routers import health, sandbox


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging("api")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    @app.middleware("http")
    async def add_request_id_header(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/")
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(sandbox.router)
    return app


app = create_app()
