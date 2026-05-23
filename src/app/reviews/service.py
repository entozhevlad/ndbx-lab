from app.events.service import EventService
from app.reviews.cache import ReviewCache
from app.reviews.store import Review, ReviewStore


class ReviewAlreadyExistsError(Exception):
    pass


class EventNotFoundError(Exception):
    pass


class ReviewNotFoundError(Exception):
    pass


class ReviewService:
    def __init__(
        self,
        event_service: EventService,
        review_store: ReviewStore,
        review_cache: ReviewCache,
    ) -> None:
        self._event_service = event_service
        self._review_store = review_store
        self._review_cache = review_cache

    async def create_review(
        self,
        event_id: str,
        user_id: str,
        rating: int,
        comment: str,
    ) -> str:
        event = await self._event_service.get_event(event_id)
        if event is None:
            raise EventNotFoundError

        if await self._review_store.has_user_review(event_id, user_id):
            raise ReviewAlreadyExistsError

        review_id = await self._review_store.insert_review(
            event_id=event_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
        )

        title = _get_title(event)
        if title is not None:
            await self._refresh_cache(title)
        return review_id

    async def update_review(
        self,
        event_id: str,
        review_id: str,
        user_id: str,
        rating: int | None,
        comment: str | None,
    ) -> None:
        event = await self._event_service.get_event(event_id)
        if event is None:
            raise EventNotFoundError

        review = await self._review_store.get_review(event_id, review_id)
        if review is None or review.created_by != user_id:
            raise ReviewNotFoundError

        await self._review_store.update_review(
            review=review,
            rating=rating,
            comment=comment,
        )

        title = _get_title(event)
        if title is not None:
            await self._refresh_cache(title)

    async def list_reviews(
        self,
        event_id: str,
        limit: int | None,
        offset: int,
    ) -> list[Review]:
        return await self._review_store.list_reviews_for_event(
            event_id=event_id,
            limit=limit,
            offset=offset,
        )

    async def aggregate_by_title(self, title: str) -> tuple[int, float]:
        cached = await self._review_cache.get(title)
        if cached is not None:
            return cached

        event_ids = await self._event_service.list_event_ids_by_title(title)
        if not event_ids:
            return 0, 0.0

        count, rating = await self._review_store.aggregate_for_events(event_ids)
        if count == 0:
            return 0, 0.0

        await self._review_cache.set(title, count, rating)
        return count, rating

    async def aggregates_for_titles(
        self,
        titles: list[str],
    ) -> dict[str, tuple[int, float]]:
        result: dict[str, tuple[int, float]] = {}
        for title in titles:
            if title in result:
                continue
            result[title] = await self.aggregate_by_title(title)
        return result

    async def _refresh_cache(self, title: str) -> None:
        event_ids = await self._event_service.list_event_ids_by_title(title)
        if not event_ids:
            return

        count, rating = await self._review_store.aggregate_for_events(event_ids)
        await self._review_cache.set(title, count, rating)


def _get_title(event: dict[str, object]) -> str | None:
    value = event.get("title")
    if isinstance(value, str) and value != "":
        return value
    return None
