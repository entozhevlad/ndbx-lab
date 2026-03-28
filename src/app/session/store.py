from datetime import UTC, datetime
from typing import Awaitable, cast

from redis.asyncio import Redis
from redis.exceptions import WatchError

from app.session.types import SessionData
from app.user_session import redis_key_for_sid


class SessionStore:
    def __init__(
        self,
        redis: Redis,
        ttl_seconds: int,
        retry_attempts: int,
    ) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds
        self._retry_attempts = retry_attempts

    async def create_session(
        self,
        sid: str,
        user_id: str | None = None,
    ) -> bool:
        key = redis_key_for_sid(sid)
        now = self._now_rfc3339()
        mapping = {
            "created_at": now,
            "updated_at": now,
        }

        if user_id is not None:
            mapping["user_id"] = user_id

        for _ in range(self._retry_attempts):
            async with self._redis.pipeline() as pipe:
                try:
                    await pipe.watch(key)

                    if await pipe.exists(key):
                        return False

                    pipe.multi()
                    pipe.hset(key, mapping=mapping)
                    pipe.expire(key, self._ttl_seconds)
                    await pipe.execute()
                    return True
                except WatchError:
                    continue
                finally:
                    await pipe.reset()

        return False

    async def refresh_session(self, sid: str) -> bool:
        key = redis_key_for_sid(sid)
        now = self._now_rfc3339()

        for _ in range(self._retry_attempts):
            async with self._redis.pipeline() as pipe:
                try:
                    await pipe.watch(key)

                    if not await pipe.exists(key):
                        return False

                    pipe.multi()
                    pipe.hset(key, mapping={"updated_at": now})
                    pipe.expire(key, self._ttl_seconds)
                    await pipe.execute()
                    return True
                except WatchError:
                    continue
                finally:
                    await pipe.reset()

        return False

    async def set_user_id(self, sid: str, user_id: str) -> bool:
        key = redis_key_for_sid(sid)
        now = self._now_rfc3339()

        for _ in range(self._retry_attempts):
            async with self._redis.pipeline() as pipe:
                try:
                    await pipe.watch(key)

                    if not await pipe.exists(key):
                        return False

                    pipe.multi()
                    pipe.hset(
                        key,
                        mapping={
                            "updated_at": now,
                            "user_id": user_id,
                        },
                    )
                    pipe.expire(key, self._ttl_seconds)
                    await pipe.execute()
                    return True
                except WatchError:
                    continue
                finally:
                    await pipe.reset()

        return False

    async def get_session(self, sid: str) -> SessionData | None:
        data = await cast(
            Awaitable[dict[str, str]],
            self._redis.hgetall(redis_key_for_sid(sid)),
        )
        if not data:
            return None

        created_at = data.get("created_at")
        updated_at = data.get("updated_at")

        if created_at is None or updated_at is None:
            return None

        return SessionData(
            sid=sid,
            created_at=created_at,
            updated_at=updated_at,
            user_id=data.get("user_id"),
        )

    async def delete_session(self, sid: str) -> None:
        await self._redis.delete(redis_key_for_sid(sid))

    @staticmethod
    def _now_rfc3339() -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
