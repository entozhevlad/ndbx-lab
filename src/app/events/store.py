import re

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase


class EventStore:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self._collection = database["events"]

    async def create_event(self, document: dict[str, object]) -> str:
        result = await self._collection.insert_one(document)
        return str(result.inserted_id)

    async def get_event_by_title(self, title: str) -> dict[str, object] | None:
        return await self._collection.find_one({"title": title})

    async def get_event_by_id(self, event_id: str) -> dict[str, object] | None:
        object_id = _parse_object_id(event_id)
        if object_id is None:
            return None

        return await self._collection.find_one({"_id": object_id})

    async def list_events(
        self,
        query: dict[str, object],
        limit: int | None,
        offset: int,
    ) -> list[dict[str, object]]:
        cursor = self._collection.find(query).sort("_id", 1).skip(offset)
        if limit is not None:
            cursor = cursor.limit(limit)

        events: list[dict[str, object]] = []
        async for event in cursor:
            events.append(event)

        return events

    async def update_event(
        self,
        event_id: str,
        organizer_id: str,
        set_fields: dict[str, object],
        unset_fields: list[str],
    ) -> bool:
        object_id = _parse_object_id(event_id)
        if object_id is None:
            return False

        update: dict[str, object] = {}
        if set_fields:
            update["$set"] = set_fields
        if unset_fields:
            update["$unset"] = {field_name: "" for field_name in unset_fields}

        if not update:
            return await self.has_event_for_organizer(event_id, organizer_id)

        result = await self._collection.update_one(
            {
                "_id": object_id,
                "created_by": organizer_id,
            },
            update,
        )
        return result.matched_count > 0

    async def has_event_for_organizer(
        self,
        event_id: str,
        organizer_id: str,
    ) -> bool:
        object_id = _parse_object_id(event_id)
        if object_id is None:
            return False

        event = await self._collection.find_one(
            {
                "_id": object_id,
                "created_by": organizer_id,
            },
            projection={"_id": 1},
        )
        return event is not None


def build_title_query(title: str) -> dict[str, object]:
    if title == "":
        return {}

    return {"title": {"$regex": re.escape(title)}}


def _parse_object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None
