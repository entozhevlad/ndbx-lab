import asyncio
from collections.abc import Iterable
from datetime import UTC, datetime

from cassandra.cluster import Session
from cassandra.query import PreparedStatement

LIKE_VALUE = 1
DISLIKE_VALUE = -1


class ReactionStore:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._upsert_stmt: PreparedStatement = session.prepare(
            """
            INSERT INTO event_reactions (event_id, created_by, like_value, created_at)
            VALUES (?, ?, ?, ?)
            """
        )
        self._select_like_values_stmt: PreparedStatement = session.prepare(
            """
            SELECT like_value FROM event_reactions WHERE event_id = ?
            """
        )

    async def upsert_reaction(
        self,
        event_id: str,
        user_id: str,
        like_value: int,
    ) -> None:
        now = datetime.now(UTC)
        await asyncio.to_thread(
            self._session.execute,
            self._upsert_stmt,
            (event_id, user_id, like_value, now),
        )

    async def count_reactions_for_events(
        self,
        event_ids: Iterable[str],
    ) -> tuple[int, int]:
        unique_ids = [event_id for event_id in event_ids if event_id]
        if not unique_ids:
            return 0, 0

        return await asyncio.to_thread(self._count_sync, unique_ids)

    def _count_sync(self, event_ids: list[str]) -> tuple[int, int]:
        likes = 0
        dislikes = 0
        for event_id in event_ids:
            rows = self._session.execute(
                self._select_like_values_stmt,
                (event_id,),
            )
            for row in rows:
                if row.like_value == LIKE_VALUE:
                    likes += 1
                elif row.like_value == DISLIKE_VALUE:
                    dislikes += 1
        return likes, dislikes
