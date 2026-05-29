import json
from typing import Awaitable, cast

from redis.asyncio import Redis

_KEY_TEMPLATE = "user:{user_id}:recomms"
_EVENTS_FIELD = "events"


class RecommendationCache:
    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get(self, user_id: str) -> list[dict[str, object]] | None:
        key = _build_key(user_id)
        data = await cast(Awaitable[dict[str, str]], self._redis.hgetall(key))
        if not data:
            return None

        raw = data.get(_EVENTS_FIELD)
        if not isinstance(raw, str):
            return None

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, list):
            return None

        return [item for item in parsed if isinstance(item, dict)]

    async def set(self, user_id: str, events: list[dict[str, object]]) -> None:
        key = _build_key(user_id)
        payload = json.dumps(events, ensure_ascii=False)
        async with self._redis.pipeline() as pipe:
            pipe.delete(key)
            pipe.hset(key, mapping={_EVENTS_FIELD: payload})
            pipe.expire(key, self._ttl_seconds)
            await pipe.execute()


def _build_key(user_id: str) -> str:
    return _KEY_TEMPLATE.format(user_id=user_id)
