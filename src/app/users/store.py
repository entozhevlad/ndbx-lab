import re

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase


PUBLIC_USER_PROJECTION = {
    "full_name": 1,
    "username": 1,
}


class UserStore:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self._collection = database["users"]

    async def create_user(
        self,
        full_name: str,
        username: str,
        password_hash: str,
    ) -> str:
        result = await self._collection.insert_one(
            {
                "full_name": full_name,
                "username": username,
                "password_hash": password_hash,
            }
        )
        return str(result.inserted_id)

    async def get_user_by_username(self, username: str) -> dict[str, object] | None:
        return await self._collection.find_one({"username": username})

    async def get_public_user_by_id(
        self,
        user_id: str,
    ) -> dict[str, object] | None:
        object_id = _parse_object_id(user_id)
        if object_id is None:
            return None

        return await self._collection.find_one(
            {"_id": object_id},
            projection=PUBLIC_USER_PROJECTION,
        )

    async def list_public_users(
        self,
        name: str,
        user_id: str | None,
        limit: int | None,
        offset: int,
    ) -> list[dict[str, object]]:
        query: dict[str, object] = {}

        if name != "":
            query["full_name"] = {"$regex": re.escape(name)}

        if user_id is not None:
            object_id = _parse_object_id(user_id)
            if object_id is None:
                return []
            query["_id"] = object_id

        cursor = self._collection.find(
            query,
            projection=PUBLIC_USER_PROJECTION,
        ).sort("_id", 1).skip(offset)

        if limit is not None:
            cursor = cursor.limit(limit)

        users: list[dict[str, object]] = []
        async for user in cursor:
            users.append(user)

        return users


def _parse_object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None
