from dataclasses import dataclass

from redis.asyncio import Redis

from app.config import Settings
from app.session.service import SessionService
from app.session.store import SessionStore


@dataclass(frozen=True, slots=True)
class SessionModule:
    store: SessionStore
    service: SessionService


def init_session_module(settings: Settings, redis: Redis) -> SessionModule:
    store = SessionStore(
        redis=redis,
        ttl_seconds=settings.app_user_session_ttl,
        retry_attempts=settings.app_user_session_store_retry_attempts,
    )
    service = SessionService(
        session_store=store,
        max_attempts=settings.app_user_session_create_max_attempts,
    )

    return SessionModule(
        store=store,
        service=service,
    )