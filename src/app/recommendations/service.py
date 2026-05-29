from datetime import UTC, datetime

from app.events.service import EventService
from app.recommendations.cache import RecommendationCache
from app.recommendations.store import RecommendationStore


class RecommendationService:
    def __init__(
        self,
        event_service: EventService,
        recommendation_store: RecommendationStore,
        recommendation_cache: RecommendationCache,
    ) -> None:
        self._event_service = event_service
        self._recommendation_store = recommendation_store
        self._recommendation_cache = recommendation_cache

    async def sync_user(self, user_id: str) -> None:
        await self._recommendation_store.upsert_user(user_id)

    async def sync_event(self, event_id: str, title: str) -> None:
        await self._recommendation_store.upsert_event(event_id, title)

    async def record_like(self, user_id: str, event_id: str) -> None:
        await self._recommendation_store.record_like(user_id, event_id)

    async def get_recommendations(
        self,
        user_id: str,
    ) -> list[dict[str, object]]:
        cached = await self._recommendation_cache.get(user_id)
        if cached is not None:
            return cached

        ranked_ids = await self._recommendation_store.recommend_event_ids(user_id)
        if not ranked_ids:
            await self._recommendation_cache.set(user_id, [])
            return []

        events = await self._event_service.list_events_by_ids(ranked_ids)
        events_by_id = {
            event["id"]: event for event in events if isinstance(event["id"], str)
        }

        ordered: list[dict[str, object]] = []
        for event_id in ranked_ids:
            event = events_by_id.get(event_id)
            if event is not None:
                ordered.append(event)

        deduplicated = _deduplicate_by_title(ordered)
        await self._recommendation_cache.set(user_id, deduplicated)
        return deduplicated


def _deduplicate_by_title(
    events: list[dict[str, object]],
) -> list[dict[str, object]]:
    chosen: dict[str, dict[str, object]] = {}
    order: list[str] = []
    now = datetime.now(UTC)

    for event in events:
        title = event.get("title")
        if not isinstance(title, str) or title == "":
            continue

        if title not in chosen:
            chosen[title] = event
            order.append(title)
            continue

        if _is_closer(event, chosen[title], now):
            chosen[title] = event

    return [chosen[title] for title in order]


def _is_closer(
    candidate: dict[str, object],
    current: dict[str, object],
    now: datetime,
) -> bool:
    candidate_dt = _parse_started_at(candidate.get("started_at"))
    current_dt = _parse_started_at(current.get("started_at"))
    if candidate_dt is None:
        return False
    if current_dt is None:
        return True
    return abs((candidate_dt - now).total_seconds()) < abs(
        (current_dt - now).total_seconds()
    )


def _parse_started_at(value: object) -> datetime | None:
    if not isinstance(value, str) or value == "":
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
