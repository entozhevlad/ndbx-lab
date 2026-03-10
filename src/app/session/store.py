from datetime import UTC, datetime

from redis.asyncio import Redis
from redis.exceptions import WatchError

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

    async def create_session(self, sid: str) -> bool:
        key = redis_key_for_sid(sid)
        now = self._now_rfc3339()

        for _ in range(self._retry_attempts):
            async with self._redis.pipeline() as pipe:
                try:
                    await pipe.watch(key)

                    if await pipe.exists(key):
                        return False

                    pipe.multi()
                    pipe.hset(
                        key,
                        mapping={
                            "created_at": now,
                            "updated_at": now,
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

    @staticmethod
    def _now_rfc3339() -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")