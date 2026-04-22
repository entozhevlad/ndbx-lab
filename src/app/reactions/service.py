from app.events.service import EventService
from app.reactions.cache import ReactionCache
from app.reactions.store import DISLIKE_VALUE, LIKE_VALUE, ReactionStore


class ReactionService:
    def __init__(
        self,
        event_service: EventService,
        reaction_store: ReactionStore,
        reaction_cache: ReactionCache,
    ) -> None:
        self._event_service = event_service
        self._reaction_store = reaction_store
        self._reaction_cache = reaction_cache

    async def put_like(self, event_id: str, user_id: str) -> bool:
        return await self._put_reaction(event_id, user_id, LIKE_VALUE)

    async def put_dislike(self, event_id: str, user_id: str) -> bool:
        return await self._put_reaction(event_id, user_id, DISLIKE_VALUE)

    async def _put_reaction(
        self,
        event_id: str,
        user_id: str,
        like_value: int,
    ) -> bool:
        event = await self._event_service.get_event(event_id)
        if event is None:
            return False

        await self._reaction_store.upsert_reaction(
            event_id=event_id,
            user_id=user_id,
            like_value=like_value,
        )

        title = _get_title(event)
        if title is not None:
            await self._invalidate_cache(title)
        return True

    async def count_by_title(self, title: str) -> tuple[int, int]:
        cached = await self._reaction_cache.get(title)
        if cached is not None:
            return cached

        event_ids = await self._event_service.list_event_ids_by_title(title)
        if not event_ids:
            return 0, 0

        likes, dislikes = await self._reaction_store.count_reactions_for_events(
            event_ids
        )
        if likes == 0 and dislikes == 0:
            return 0, 0

        await self._reaction_cache.set(title, likes, dislikes)
        return likes, dislikes

    async def counts_for_titles(
        self,
        titles: list[str],
    ) -> dict[str, tuple[int, int]]:
        result: dict[str, tuple[int, int]] = {}
        for title in titles:
            if title in result:
                continue
            result[title] = await self.count_by_title(title)
        return result

    async def _invalidate_cache(self, title: str) -> None:
        event_ids = await self._event_service.list_event_ids_by_title(title)
        if not event_ids:
            return

        likes, dislikes = await self._reaction_store.count_reactions_for_events(
            event_ids
        )
        if likes == 0 and dislikes == 0:
            return

        await self._reaction_cache.set(title, likes, dislikes)


def _get_title(event: dict[str, object]) -> str | None:
    value = event.get("title")
    if isinstance(value, str) and value != "":
        return value
    return None
