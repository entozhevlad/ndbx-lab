from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from redis.asyncio import Redis

from app.config import load_settings
from app.session.bootstrap import init_session_module


def create_app(root_message: str = "Welcome") -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = load_settings()

        redis = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password or None,
            db=settings.redis_db,
            decode_responses=True,
        )

        session_module = init_session_module(
            settings=settings,
            redis=redis,
        )

        app.state.settings = settings
        app.state.redis = redis
        app.state.session_module = session_module

        try:
            yield
        finally:
            await redis.aclose()

    app = FastAPI(lifespan=lifespan)

    @app.middleware("http")
    async def root_response(request: Request, call_next):
        if request.url.path == "/":
            return PlainTextResponse(root_message)
        return await call_next(request)

    return app