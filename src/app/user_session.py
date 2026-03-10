import re
import secrets
from typing import Final

from fastapi import Response

COOKIE_NAME: Final[str] = "X-Session-Id"
REDIS_SESSION_KEY_PREFIX: Final[str] = "sid:"
SID_BITS: Final[int] = 128
SID_SIZE_BYTES: Final[int] = SID_BITS // 8
SID_HEX_LENGTH: Final[int] = SID_SIZE_BYTES * 2
SID_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"^[0-9a-f]{{{SID_HEX_LENGTH}}}$"
)


def generate_sid() -> str:
    return secrets.token_hex(SID_SIZE_BYTES)


def is_valid_sid(sid: str) -> bool:
    return bool(SID_PATTERN.fullmatch(sid))


def redis_key_for_sid(sid: str) -> str:
    return f"{REDIS_SESSION_KEY_PREFIX}{sid}"


def set_session_cookie(response: Response, sid: str, ttl_seconds: int) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=sid,
        httponly=True,
        path="/",
        max_age=ttl_seconds,
    )