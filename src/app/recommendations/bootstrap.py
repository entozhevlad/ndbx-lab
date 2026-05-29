from dataclasses import dataclass

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.config import Settings


@dataclass(frozen=True, slots=True)
class Neo4jModule:
    driver: AsyncDriver


async def init_neo4j_module(settings: Settings) -> Neo4jModule:
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_url,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )
    await driver.verify_connectivity()
    return Neo4jModule(driver=driver)


async def close_neo4j_module(module: Neo4jModule) -> None:
    await module.driver.close()
