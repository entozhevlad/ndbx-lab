from datetime import UTC, datetime

from bson import ObjectId
from bson.errors import InvalidId

from app.events.store import EventStore, build_title_query


class EventAlreadyExistsError(Exception):
    pass


EVENT_CATEGORIES = frozenset(
    {
        "meetup",
        "concert",
        "exhibition",
        "party",
        "other",
    }
)


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
        existing_event = await self._event_store.get_event_by_title(title)
        if existing_event is not None:
            raise EventAlreadyExistsError

        document: dict[str, object] = {
            "title": title,
            "description": description,
            "location": {"address": address},
            "created_at": self._now_rfc3339(),
            "created_by": user_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "started_day": _extract_day_key(started_at),
        }

        return await self._event_store.create_event(document)

    async def list_events(
        self,
        title: str,
        event_id: str | None,
        category: str | None,
        price_from: int | None,
        price_to: int | None,
        city: str | None,
        date_from: str | None,
        date_to: str | None,
        created_by: str | None,
        limit: int | None,
        offset: int,
    ) -> list[dict[str, object]]:
        query = build_title_query(title)

        if event_id is not None:
            object_id = _parse_object_id(event_id)
            if object_id is None:
                return []
            query["_id"] = object_id

        if category is not None:
            query["category"] = category

        if price_from is not None or price_to is not None:
            price_query: dict[str, int] = {}
            if price_from is not None:
                price_query["$gte"] = price_from
            if price_to is not None:
                price_query["$lte"] = price_to
            query["price"] = price_query

        if city is not None:
            query["location.city"] = city

        if date_from is not None or date_to is not None:
            day_expr: dict[str, object] = {
                "$substrBytes": ["$started_at", 0, 10]
            }
            conditions: list[dict[str, object]] = []
            if date_from is not None:
                conditions.append({"$gte": [day_expr, _iso_day(date_from)]})
            if date_to is not None:
                conditions.append({"$lte": [day_expr, _iso_day(date_to)]})
            query["$expr"] = {"$and": conditions}

        if created_by is not None:
            query["created_by"] = created_by

        events = await self._event_store.list_events(
            query=query,
            limit=limit,
            offset=offset,
        )
        return [self._serialize_event(event) for event in events]

    async def get_event(self, event_id: str) -> dict[str, object] | None:
        event = await self._event_store.get_event_by_id(event_id)
        if event is None:
            return None

        return self._serialize_event(event)

    async def list_event_ids_by_title(self, title: str) -> list[str]:
        if title == "":
            return []

        return await self._event_store.list_event_ids_by_title(title)

    async def update_event(
        self,
        event_id: str,
        organizer_id: str,
        category: str | None,
        price: int | None,
        city: str | None,
        clear_city: bool,
    ) -> bool:
        set_fields: dict[str, object] = {}
        unset_fields: list[str] = []

        if category is not None:
            set_fields["category"] = category

        if price is not None:
            set_fields["price"] = price

        if clear_city:
            unset_fields.append("location.city")
        elif city is not None:
            set_fields["location.city"] = city

        return await self._event_store.update_event(
            event_id=event_id,
            organizer_id=organizer_id,
            set_fields=set_fields,
            unset_fields=unset_fields,
        )

    @staticmethod
    def _serialize_event(event: dict[str, object]) -> dict[str, object]:
        location = event.get("location")
        address = ""
        city = None
        if isinstance(location, dict):
            raw_address = location.get("address")
            if isinstance(raw_address, str):
                address = raw_address
            raw_city = location.get("city")
            if isinstance(raw_city, str):
                city = raw_city

        serialized: dict[str, object] = {
            "id": str(event.get("_id", "")),
            "title": _get_string(event.get("title")),
            "description": _get_string(event.get("description")),
            "location": {"address": address},
            "created_at": _get_string(event.get("created_at")),
            "created_by": _get_string(event.get("created_by")),
            "started_at": _get_string(event.get("started_at")),
            "finished_at": _get_string(event.get("finished_at")),
        }

        if city is not None:
            location_data = serialized["location"]
            if isinstance(location_data, dict):
                location_data["city"] = city

        category = event.get("category")
        if isinstance(category, str):
            serialized["category"] = category

        price = event.get("price")
        if isinstance(price, int) and not isinstance(price, bool):
            serialized["price"] = price

        return serialized

    @staticmethod
    def _now_rfc3339() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds").replace(
            "+00:00",
            "Z",
        )


def _get_string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _extract_day_key(value: str) -> str:
    return value[:10].replace("-", "")


def _iso_day(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def _parse_object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None
