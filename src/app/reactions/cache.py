import hashlib
from typing import Awaitable, cast

from redis.asyncio import Redis

_KEY_TEMPLATE = "event:{title_hash}:reactions"
_LIKES_FIELD = "likes"
_DISLIKES_FIELD = "dislikes"


class ReactionCache:
    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get(self, title: str) -> tuple[int, int] | None:
        key = _build_key(title)
        data = await cast(Awaitable[dict[str, str]], self._redis.hgetall(key))
        if not data:
            return None

        likes = _parse_int(data.get(_LIKES_FIELD))
        dislikes = _parse_int(data.get(_DISLIKES_FIELD))
        if likes is None or dislikes is None:
            return None

        return likes, dislikes

    async def set(self, title: str, likes: int, dislikes: int) -> None:
        key = _build_key(title)
        async with self._redis.pipeline() as pipe:
            pipe.delete(key)
            pipe.hset(
                key,
                mapping={
                    _LIKES_FIELD: likes,
                    _DISLIKES_FIELD: dislikes,
                },
            )
            pipe.expire(key, self._ttl_seconds)
            await pipe.execute()


def _build_key(title: str) -> str:
    digest = hashlib.md5(title.encode("utf-8")).hexdigest()
    return _KEY_TEMPLATE.format(title_hash=digest)


def _parse_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
