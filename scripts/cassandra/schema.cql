-- Схема таблиц Cassandra для реакций и отзывов на мероприятия.
-- Применяется в контексте keyspace, переданного через cqlsh -k.

CREATE TABLE IF NOT EXISTS event_reactions (
    event_id text,
    created_by text,
    like_value tinyint,
    created_at timestamp,
    PRIMARY KEY ((event_id), created_by)
);

CREATE INDEX IF NOT EXISTS event_reactions_like_value_idx
ON event_reactions (like_value);

CREATE INDEX IF NOT EXISTS event_reactions_created_by_idx
ON event_reactions (created_by);

CREATE TABLE IF NOT EXISTS event_reviews (
    event_id text,
    created_at timestamp,
    id uuid,
    rating tinyint,
    comment text,
    created_by text,
    updated_at timestamp,
    PRIMARY KEY ((event_id), created_at, id)
) WITH CLUSTERING ORDER BY (created_at DESC, id ASC);

CREATE INDEX IF NOT EXISTS event_reviews_created_by_idx
ON event_reviews (created_by);

CREATE INDEX IF NOT EXISTS event_reviews_id_idx
ON event_reviews (id);
