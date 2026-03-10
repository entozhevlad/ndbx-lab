from typing import Protocol

from app.session.types import SessionUpsertResult
from app.user_session import generate_sid


class SessionStoreProtocol(Protocol):
    async def create_session(self, sid: str) -> bool: ...
    async def refresh_session(self, sid: str) -> bool: ...


class SessionService:
    def __init__(self, session_store: SessionStoreProtocol, max_attempts: int) -> None:
        self._session_store = session_store
        self._max_attempts = max_attempts

    async def create_or_refresh_session(self, sid: str | None) -> SessionUpsertResult:
        if sid is not None:
            refreshed = await self._session_store.refresh_session(sid)
            if refreshed:
                return SessionUpsertResult(sid=sid, is_created=False)

        new_sid = await self._create_new_session()
        return SessionUpsertResult(sid=new_sid, is_created=True)

    async def _create_new_session(self) -> str:
        for _ in range(self._max_attempts):
            sid = generate_sid()
            created = await self._session_store.create_session(sid)
            if created:
                return sid

        raise RuntimeError("не получилось создать сессию")