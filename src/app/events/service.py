from datetime import UTC, datetime

from pymongo.errors import DuplicateKeyError

from app.events.store import EventStore


class EventAlreadyExistsError(Exception):
    pass


class EventService:
    def __init__(self, event_store: EventStore) -> None:
        self._event_store = event_store

    async def create_event(
        self,
        title: str,
        address: str,
        started_at: str,
        finished_at: str,
        description: str,
        user_id: str,
    ) -> str:
        document: dict[str, object] = {
            "title": title,
            "description": description,
            "location": {"address": address},
            "created_at": self._now_rfc3339(),
            "created_by": user_id,
            "started_at": started_at,
            "finished_at": finished_at,
        }

        try:
            return await self._event_store.create_event(document)
        except DuplicateKeyError as exc:
            raise EventAlreadyExistsError from exc

    async def list_events(
        self,
        title: str,
        limit: int | None,
        offset: int,
    ) -> list[dict[str, object]]:
        events = await self._event_store.list_events(
            title=title,
            limit=limit,
            offset=offset,
        )
        return [self._serialize_event(event) for event in events]

    @staticmethod
    def _serialize_event(event: dict[str, object]) -> dict[str, object]:
        location = event.get("location")
        address = ""
        if isinstance(location, dict):
            raw_address = location.get("address")
            if isinstance(raw_address, str):
                address = raw_address

        return {
            "id": str(event.get("_id", "")),
            "title": _get_string(event.get("title")),
            "description": _get_string(event.get("description")),
            "location": {"address": address},
            "created_at": _get_string(event.get("created_at")),
            "created_by": _get_string(event.get("created_by")),
            "started_at": _get_string(event.get("started_at")),
            "finished_at": _get_string(event.get("finished_at")),
        }

    @staticmethod
    def _now_rfc3339() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds").replace(
            "+00:00",
            "Z",
        )


def _get_string(value: object) -> str:
    return value if isinstance(value, str) else ""
