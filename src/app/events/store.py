import re

from motor.motor_asyncio import AsyncIOMotorDatabase


class EventStore:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self._collection = database["events"]

    async def create_event(self, document: dict[str, object]) -> str:
        result = await self._collection.insert_one(document)
        return str(result.inserted_id)

    async def list_events(
        self,
        title: str,
        limit: int | None,
        offset: int,
    ) -> list[dict[str, object]]:
        query: dict[str, object] = {}
        if title != "":
            query["title"] = {"$regex": re.escape(title)}

        cursor = self._collection.find(query).sort("_id", 1).skip(offset)
        if limit is not None:
            cursor = cursor.limit(limit)

        events: list[dict[str, object]] = []
        async for event in cursor:
            events.append(event)

        return events
