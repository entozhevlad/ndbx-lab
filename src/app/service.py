from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from redis.asyncio import Redis

from app.auth.service import AuthService
from app.cassandra.bootstrap import (close_cassandra_module,
                                     init_cassandra_module)
from app.config import load_settings
from app.events.service import EventService
from app.events.store import EventStore
from app.mongodb.bootstrap import init_mongodb_module
from app.reactions.cache import ReactionCache
from app.reactions.service import ReactionService
from app.reactions.store import ReactionStore
from app.reviews.cache import ReviewCache
from app.reviews.service import ReviewService
from app.reviews.store import ReviewStore
from app.session.bootstrap import init_session_module
from app.users.service import UserService
from app.users.store import UserStore


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

        mongo_module = None
        cassandra_module = None

        try:
            session_module = init_session_module(
                settings=settings,
                redis=redis,
            )
            mongo_module = await init_mongodb_module(settings)
            cassandra_module = await init_cassandra_module(settings)

            user_store = UserStore(mongo_module.database)
            event_store = EventStore(mongo_module.database)

            user_service = UserService(user_store)
            event_service = EventService(event_store)
            auth_service = AuthService(
                user_service=user_service,
                session_service=session_module.service,
            )

            reaction_store = ReactionStore(cassandra_module.session)
            reaction_cache = ReactionCache(
                redis=redis,
                ttl_seconds=settings.app_like_ttl,
            )
            reaction_service = ReactionService(
                event_service=event_service,
                reaction_store=reaction_store,
                reaction_cache=reaction_cache,
            )

            review_store = ReviewStore(cassandra_module.session)
            review_cache = ReviewCache(
                redis=redis,
                ttl_seconds=settings.app_event_reviews_ttl,
            )
            review_service = ReviewService(
                event_service=event_service,
                review_store=review_store,
                review_cache=review_cache,
            )

            app.state.settings = settings
            app.state.redis = redis
            app.state.mongodb = mongo_module
            app.state.cassandra = cassandra_module
            app.state.session_module = session_module
            app.state.user_service = user_service
            app.state.event_service = event_service
            app.state.auth_service = auth_service
            app.state.reaction_service = reaction_service
            app.state.review_service = review_service

            yield
        finally:
            if mongo_module is not None:
                mongo_module.client.close()
            if cassandra_module is not None:
                close_cassandra_module(cassandra_module)
            await redis.aclose()

    app = FastAPI(lifespan=lifespan)

    @app.middleware("http")
    async def root_response(request: Request, call_next):
        if request.url.path == "/":
            return PlainTextResponse(root_message)
        return await call_next(request)

    return app
