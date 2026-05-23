import hashlib
from typing import Awaitable, cast

from redis.asyncio import Redis

_KEY_TEMPLATE = "event:{title_hash}:reviews"
_COUNT_FIELD = "count"
_RATING_FIELD = "rating"


class ReviewCache:
    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get(self, title: str) -> tuple[int, float] | None:
        key = _build_key(title)
        data = await cast(Awaitable[dict[str, str]], self._redis.hgetall(key))
        if not data:
            return None

        count = _parse_int(data.get(_COUNT_FIELD))
        rating = _parse_float(data.get(_RATING_FIELD))
        if count is None or rating is None:
            return None

        return count, rating

    async def set(self, title: str, count: int, rating: float) -> None:
        key = _build_key(title)
        async with self._redis.pipeline() as pipe:
            pipe.delete(key)
            pipe.hset(
                key,
                mapping={
                    _COUNT_FIELD: count,
                    _RATING_FIELD: _format_rating(rating),
                },
            )
            pipe.expire(key, self._ttl_seconds)
            await pipe.execute()


def _build_key(title: str) -> str:
    digest = hashlib.md5(title.encode("utf-8")).hexdigest()
    return _KEY_TEMPLATE.format(title_hash=digest)


def _format_rating(value: float) -> str:
    return f"{round(value, 1):.1f}"


def _parse_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _parse_float(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None
