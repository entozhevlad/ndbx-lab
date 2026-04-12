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
    redis_host: str
    redis_port: int
    redis_password: str
    redis_db: int
    mongodb_host: str
    mongodb_port: int
    mongodb_username: str
    mongodb_password: str
    mongodb_db: str


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
        mongodb_username=_get_env("MONGODB_USER", "MONGODB_USERNAME") or "",
        mongodb_password=_get_env("MONGODB_PASSWORD") or "",
        mongodb_db=_require_env("MONGODB_DATABASE"),
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
    _require_positive(settings.redis_port, "REDIS_PORT")
    _require_positive(settings.mongodb_port, "MONGODB_PORT")

    if settings.mongodb_db.strip() == "":
        raise ValueError("MONGODB_DATABASE не должен быть пустым")

    return settings


def _require_positive(value: int, env_name: str) -> None:
    if value <= 0:
        raise ValueError(f"{env_name} должно быть > 0")


def _require_env(*names: str) -> str:
    value = _get_env(*names)
    if value is None:
        joined_names = ", ".join(names)
        raise KeyError(joined_names)

    return value


def _get_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value is not None:
            return value

    return None
