import hashlib
import json

from redis.asyncio import Redis

_KEY_TEMPLATE = "events:{title_hash}:reactions"


class ReactionCache:
    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get(self, title: str) -> tuple[int, int] | None:
        raw = await self._redis.get(_build_key(title))
        if raw is None:
            return None

        try:
            data = json.loads(raw)
        except ValueError:
            return None

        likes = data.get("likes")
        dislikes = data.get("dislikes")
        if not isinstance(likes, int) or not isinstance(dislikes, int):
            return None

        return likes, dislikes

    async def set(self, title: str, likes: int, dislikes: int) -> None:
        await self._redis.set(
            _build_key(title),
            json.dumps({"likes": likes, "dislikes": dislikes}),
            ex=self._ttl_seconds,
        )


def _build_key(title: str) -> str:
    digest = hashlib.md5(title.encode("utf-8")).hexdigest()
    return _KEY_TEMPLATE.format(title_hash=digest)
