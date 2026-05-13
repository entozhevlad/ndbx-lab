import asyncio
from dataclasses import dataclass

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, Session
from cassandra.policies import DCAwareRoundRobinPolicy

from app.config import Settings


@dataclass(frozen=True, slots=True)
class CassandraModule:
    cluster: Cluster
    session: Session
    keyspace: str


async def init_cassandra_module(settings: Settings) -> CassandraModule:
    return await asyncio.to_thread(_init_sync, settings)


def _init_sync(settings: Settings) -> CassandraModule:
    auth_provider = None
    if settings.cassandra_username and settings.cassandra_password:
        auth_provider = PlainTextAuthProvider(
            username=settings.cassandra_username,
            password=settings.cassandra_password,
        )

    cluster = Cluster(
        contact_points=list(settings.cassandra_hosts),
        port=settings.cassandra_port,
        auth_provider=auth_provider,
        load_balancing_policy=DCAwareRoundRobinPolicy(),
        protocol_version=5,
    )
    session = cluster.connect()
    session.default_consistency_level = _consistency_level(
        settings.cassandra_consistency
    )

    keyspace = settings.cassandra_keyspace
    session.execute(
        f"""
        CREATE KEYSPACE IF NOT EXISTS {keyspace}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """
    )
    session.set_keyspace(keyspace)

    session.execute(
        """
        CREATE TABLE IF NOT EXISTS event_reactions (
            event_id text,
            created_by text,
            like_value tinyint,
            created_at timestamp,
            PRIMARY KEY ((event_id), created_by)
        )
        """
    )
    session.execute(
        """
        CREATE INDEX IF NOT EXISTS event_reactions_like_value_idx
        ON event_reactions (like_value)
        """
    )
    session.execute(
        """
        CREATE INDEX IF NOT EXISTS event_reactions_created_by_idx
        ON event_reactions (created_by)
        """
    )

    session.execute(
        """
        CREATE TABLE IF NOT EXISTS event_reviews (
            event_id text,
            created_at timestamp,
            id uuid,
            rating tinyint,
            comment text,
            created_by text,
            updated_at timestamp,
            PRIMARY KEY ((event_id), created_at, id)
        ) WITH CLUSTERING ORDER BY (created_at DESC, id ASC)
        """
    )
    session.execute(
        """
        CREATE INDEX IF NOT EXISTS event_reviews_created_by_idx
        ON event_reviews (created_by)
        """
    )
    session.execute(
        """
        CREATE INDEX IF NOT EXISTS event_reviews_id_idx
        ON event_reviews (id)
        """
    )

    return CassandraModule(
        cluster=cluster,
        session=session,
        keyspace=keyspace,
    )


def _consistency_level(name: str) -> int:
    from cassandra import ConsistencyLevel

    try:
        return int(getattr(ConsistencyLevel, name.upper()))
    except AttributeError as exc:
        raise ValueError(
            f"Unknown CASSANDRA_CONSISTENCY value: {name}"
        ) from exc


def close_cassandra_module(module: CassandraModule) -> None:
    module.cluster.shutdown()
