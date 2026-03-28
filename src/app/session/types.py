from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionUpsertResult:
    sid: str
    is_created: bool


@dataclass(frozen=True, slots=True)
class SessionData:
    sid: str
    created_at: str
    updated_at: str
    user_id: str | None = None
