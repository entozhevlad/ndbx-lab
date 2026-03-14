import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    app_host: str
    app_port: int
    app_user_session_ttl: int
    app_user_session_create_max_attempts: int
    app_user_session_store_retry_attempts: int
    redis_host: str
    redis_port: int
    redis_password: str
    redis_db: int


def load_settings() -> Settings:
    settings = Settings(
        app_host=os.environ["APP_HOST"],
        app_port=int(os.environ["APP_PORT"]),
        app_user_session_ttl=int(os.environ["APP_USER_SESSION_TTL"]),
        app_user_session_create_max_attempts=int(
            os.environ["APP_USER_SESSION_CREATE_MAX_ATTEMPTS"]
        ),
        app_user_session_store_retry_attempts=int(
            os.environ["APP_USER_SESSION_STORE_RETRY_ATTEMPTS"]
        ),
        redis_host=os.environ["REDIS_HOST"],
        redis_port=int(os.environ["REDIS_PORT"]),
        redis_password=os.getenv("REDIS_PASSWORD"),
        redis_db=int(os.getenv("REDIS_DB")),
    )

    if settings.app_user_session_ttl <= 0:
        raise ValueError("APP_USER_SESSION_TTL должно быть > 0")

    if settings.app_user_session_create_max_attempts <= 0:
        raise ValueError(
            "APP_USER_SESSION_CREATE_MAX_ATTEMPTS должно быть > 0"
        )

    if settings.app_user_session_store_retry_attempts <= 0:
        raise ValueError(
            "APP_USER_SESSION_STORE_RETRY_ATTEMPTS должно быть > 0"
        )

    return settings
