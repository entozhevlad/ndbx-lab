from neo4j import AsyncDriver


class RecommendationStore:
    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def upsert_user(self, user_id: str) -> None:
        await self._driver.execute_query(
            "MERGE (:User {id: $user_id})",
            user_id=user_id,
        )

    async def upsert_event(self, event_id: str, title: str) -> None:
        await self._driver.execute_query(
            """
            MERGE (e:Event {id: $event_id})
            SET e.title = $title
            """,
            event_id=event_id,
            title=title,
        )

    async def record_like(self, user_id: str, event_id: str) -> None:
        await self._driver.execute_query(
            """
            MERGE (u:User {id: $user_id})
            MERGE (e:Event {id: $event_id})
            MERGE (u)-[:LIKED]->(e)
            """,
            user_id=user_id,
            event_id=event_id,
        )

    async def recommend_event_ids(self, user_id: str) -> list[str]:
        records, _, _ = await self._driver.execute_query(
            """
            MATCH (u:User {id: $user_id})-[:LIKED]->(:Event)<-[:LIKED]-(other:User)
            WHERE other.id <> $user_id
            MATCH (other)-[:LIKED]->(rec:Event)
            WHERE NOT (u)-[:LIKED]->(rec)
            RETURN rec.id AS id, count(*) AS score
            ORDER BY score DESC, rec.id ASC
            """,
            user_id=user_id,
        )
        return [record["id"] for record in records]
