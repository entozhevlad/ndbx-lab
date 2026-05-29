import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    app_host: str
    app_port: int
    app_user_session_ttl: int
    app_user_session_create_max_attempts: int
    app_user_session_store_retry_attempts: int
    app_like_ttl: int
    app_event_reviews_ttl: int
    redis_host: str
    redis_port: int
    redis_password: str
    redis_db: int
    mongodb_host: str
    mongodb_port: int
    mongodb_username: str
    mongodb_password: str
    mongodb_db: str
    cassandra_hosts: tuple[str, ...]
    cassandra_port: int
    cassandra_username: str
    cassandra_password: str
    cassandra_keyspace: str
    cassandra_consistency: str
    neo4j_url: str
    neo4j_username: str
    neo4j_password: str
    app_recommendations_ttl: int


def load_settings() -> Settings:
    load_dotenv(".env.local", override=False)

    settings = Settings(
        app_host=_require_env("APP_HOST"),
        app_port=int(_require_env("APP_PORT")),
        app_user_session_ttl=int(_require_env("APP_USER_SESSION_TTL")),
        app_user_session_create_max_attempts=int(
            _require_env("APP_USER_SESSION_CREATE_MAX_ATTEMPTS")
        ),
        app_user_session_store_retry_attempts=int(
            _require_env("APP_USER_SESSION_STORE_RETRY_ATTEMPTS")
        ),
        redis_host=_require_env("REDIS_HOST"),
        redis_port=int(_require_env("REDIS_PORT")),
        redis_password=_require_env("REDIS_PASSWORD"),
        redis_db=int(_require_env("REDIS_DB")),
        mongodb_host=_require_env("MONGODB_HOST"),
        mongodb_port=int(_require_env("MONGODB_PORT")),
        mongodb_username=_require_env("MONGODB_USER", "MONGODB_USERNAME"),
        mongodb_password=_require_env("MONGODB_PASSWORD"),
        mongodb_db=_require_env("MONGODB_DATABASE"),
        app_like_ttl=int(_require_env("APP_LIKE_TTL")),
        app_event_reviews_ttl=int(_require_env("APP_EVENT_REVIEWS_TTL")),
        cassandra_hosts=_parse_hosts(_require_env("CASSANDRA_HOSTS")),
        cassandra_port=int(_require_env("CASSANDRA_PORT")),
        cassandra_username=_require_env("CASSANDRA_USERNAME"),
        cassandra_password=_require_env("CASSANDRA_PASSWORD"),
        cassandra_keyspace=_require_env("CASSANDRA_KEYSPACE"),
        cassandra_consistency=_require_env("CASSANDRA_CONSISTENCY"),
        neo4j_url=_require_env("NEO4J_URL"),
        neo4j_username=_require_env("NEO4J_USERNAME"),
        neo4j_password=_require_env("NEO4J_PASSWORD"),
        app_recommendations_ttl=int(_require_env("APP_RECOMMENDATIONS_TTL")),
    )

    _require_positive(settings.app_port, "APP_PORT")
    _require_positive(settings.app_user_session_ttl, "APP_USER_SESSION_TTL")
    _require_positive(
        settings.app_user_session_create_max_attempts,
        "APP_USER_SESSION_CREATE_MAX_ATTEMPTS",
    )
    _require_positive(
        settings.app_user_session_store_retry_attempts,
        "APP_USER_SESSION_STORE_RETRY_ATTEMPTS",
    )
    _require_positive(settings.app_like_ttl, "APP_LIKE_TTL")
    _require_positive(settings.app_event_reviews_ttl, "APP_EVENT_REVIEWS_TTL")
    _require_positive(settings.app_recommendations_ttl, "APP_RECOMMENDATIONS_TTL")
    _require_positive(settings.redis_port, "REDIS_PORT")
    _require_positive(settings.mongodb_port, "MONGODB_PORT")
    _require_positive(settings.cassandra_port, "CASSANDRA_PORT")

    if settings.mongodb_db.strip() == "":
        raise ValueError("MONGODB_DATABASE не должен быть пустым")

    if not settings.cassandra_hosts:
        raise ValueError("CASSANDRA_HOSTS не должен быть пустым")

    if settings.cassandra_keyspace.strip() == "":
        raise ValueError("CASSANDRA_KEYSPACE не должен быть пустым")

    if settings.neo4j_url.strip() == "":
        raise ValueError("NEO4J_URL не должен быть пустым")

    return settings


def _parse_hosts(value: str) -> tuple[str, ...]:
    return tuple(
        host.strip() for host in value.split(",") if host.strip() != ""
    )


def _require_positive(value: int, env_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{env_name} должно быть > 0")


def _require_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value is not None:
            return value

    raise KeyError(", ".join(names))
