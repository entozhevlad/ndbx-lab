import asyncio
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from cassandra.cluster import Session
from cassandra.query import PreparedStatement


@dataclass(frozen=True, slots=True)
class Review:
    id: str
    event_id: str
    rating: int
    comment: str
    created_at: datetime
    created_by: str
    updated_at: datetime


class ReviewStore:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._insert_stmt: PreparedStatement = session.prepare(
            """
            INSERT INTO event_reviews
                (event_id, created_at, id, rating, comment, created_by, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
        )
        self._select_by_event_stmt: PreparedStatement = session.prepare(
            """
            SELECT id, event_id, rating, comment, created_at, created_by, updated_at
            FROM event_reviews
            WHERE event_id = ?
            """
        )
        self._select_by_user_stmt: PreparedStatement = session.prepare(
            """
            SELECT id, created_at
            FROM event_reviews
            WHERE event_id = ? AND created_by = ?
            ALLOW FILTERING
            """
        )
        self._select_by_id_stmt: PreparedStatement = session.prepare(
            """
            SELECT id, event_id, rating, comment, created_at, created_by, updated_at
            FROM event_reviews
            WHERE event_id = ? AND id = ?
            ALLOW FILTERING
            """
        )
        self._update_full_stmt: PreparedStatement = session.prepare(
            """
            UPDATE event_reviews
            SET rating = ?, comment = ?, updated_at = ?
            WHERE event_id = ? AND created_at = ? AND id = ?
            """
        )
        self._update_rating_stmt: PreparedStatement = session.prepare(
            """
            UPDATE event_reviews
            SET rating = ?, updated_at = ?
            WHERE event_id = ? AND created_at = ? AND id = ?
            """
        )
        self._update_comment_stmt: PreparedStatement = session.prepare(
            """
            UPDATE event_reviews
            SET comment = ?, updated_at = ?
            WHERE event_id = ? AND created_at = ? AND id = ?
            """
        )

    async def has_user_review(self, event_id: str, user_id: str) -> bool:
        rows = await asyncio.to_thread(
            self._session.execute,
            self._select_by_user_stmt,
            (event_id, user_id),
        )
        for _ in rows:
            return True
        return False

    async def insert_review(
        self,
        event_id: str,
        user_id: str,
        rating: int,
        comment: str,
    ) -> str:
        review_id = uuid.uuid4()
        now = datetime.now(UTC)
        await asyncio.to_thread(
            self._session.execute,
            self._insert_stmt,
            (event_id, now, review_id, rating, comment, user_id, now),
        )
        return str(review_id)

    async def get_review(self, event_id: str, review_id: str) -> Review | None:
        try:
            review_uuid = uuid.UUID(review_id)
        except (ValueError, TypeError):
            return None

        rows = await asyncio.to_thread(
            self._session.execute,
            self._select_by_id_stmt,
            (event_id, review_uuid),
        )
        for row in rows:
            return _row_to_review(row)
        return None

    async def update_review(
        self,
        review: Review,
        rating: int | None,
        comment: str | None,
    ) -> None:
        if rating is None and comment is None:
            return

        now = datetime.now(UTC)
        review_uuid = uuid.UUID(review.id)

        if rating is not None and comment is not None:
            stmt = self._update_full_stmt
            params: tuple[object, ...] = (
                rating,
                comment,
                now,
                review.event_id,
                review.created_at,
                review_uuid,
            )
        elif rating is not None:
            stmt = self._update_rating_stmt
            params = (
                rating,
                now,
                review.event_id,
                review.created_at,
                review_uuid,
            )
        else:
            stmt = self._update_comment_stmt
            params = (
                comment,
                now,
                review.event_id,
                review.created_at,
                review_uuid,
            )

        await asyncio.to_thread(self._session.execute, stmt, params)

    async def list_reviews_for_event(
        self,
        event_id: str,
        limit: int | None,
        offset: int,
    ) -> list[Review]:
        rows = await asyncio.to_thread(
            self._session.execute,
            self._select_by_event_stmt,
            (event_id,),
        )

        reviews: list[Review] = []
        skipped = 0
        for row in rows:
            if skipped < offset:
                skipped += 1
                continue
            reviews.append(_row_to_review(row))
            if limit is not None and len(reviews) >= limit:
                break
        return reviews

    async def aggregate_for_events(
        self,
        event_ids: Iterable[str],
    ) -> tuple[int, float]:
        unique_ids = [event_id for event_id in event_ids if event_id]
        if not unique_ids:
            return 0, 0.0

        return await asyncio.to_thread(self._aggregate_sync, unique_ids)

    def _aggregate_sync(self, event_ids: list[str]) -> tuple[int, float]:
        count = 0
        total = 0
        for event_id in event_ids:
            rows = self._session.execute(
                self._select_by_event_stmt,
                (event_id,),
            )
            for row in rows:
                count += 1
                total += int(row.rating)
        if count == 0:
            return 0, 0.0
        return count, total / count


def _row_to_review(row: Any) -> Review:
    return Review(
        id=str(row.id),
        event_id=row.event_id,
        rating=int(row.rating),
        comment=row.comment or "",
        created_at=_as_utc(row.created_at),
        created_by=row.created_by,
        updated_at=_as_utc(row.updated_at),
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
