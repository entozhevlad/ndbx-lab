from dataclasses import dataclass
from urllib.parse import quote_plus

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING

from app.config import Settings


@dataclass(frozen=True, slots=True)
class MongoModule:
    client: AsyncIOMotorClient
    database: AsyncIOMotorDatabase


async def init_mongodb_module(settings: Settings) -> MongoModule:
    client: AsyncIOMotorClient = AsyncIOMotorClient(
        _build_mongodb_uri(settings)
    )
    database = client[settings.mongodb_db]

    await client.admin.command("ping")
    await database["users"].create_index("username", unique=True)
    await database["events"].create_index("title")
    await database["events"].create_index("created_by")
    await database["events"].create_index(
        [
            ("title", ASCENDING),
            ("created_by", ASCENDING),
        ]
    )
    await database["events"].create_index("category")
    await database["events"].create_index("price")
    await database["events"].create_index("location.city")

    return MongoModule(
        client=client,
        database=database,
    )


def _build_mongodb_uri(settings: Settings) -> str:
    auth = ""
    if settings.mongodb_username and settings.mongodb_password:
        username = quote_plus(settings.mongodb_username)
        password = quote_plus(settings.mongodb_password)
        auth = f"{username}:{password}@"

    return (
        f"mongodb://{auth}{settings.mongodb_host}:{settings.mongodb_port}/"
    )
