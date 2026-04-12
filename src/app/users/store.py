from motor.motor_asyncio import AsyncIOMotorDatabase


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
