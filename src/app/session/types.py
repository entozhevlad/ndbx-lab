from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionUpsertResult:
    sid: str
    is_created: bool