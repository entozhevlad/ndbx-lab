from app.session.store import SessionStore
from app.session.types import SessionData, SessionUpsertResult
from app.user_session import generate_sid


class SessionService:
    def __init__(self, session_store: SessionStore, max_attempts: int) -> None:
        self._session_store = session_store
        self._max_attempts = max_attempts

    async def create_or_refresh_session(self, sid: str | None) -> SessionUpsertResult:
        if sid is not None:
            refreshed = await self._session_store.refresh_session(sid)
            if refreshed:
                return SessionUpsertResult(sid=sid, is_created=False)

        new_sid = await self._create_new_session()
        return SessionUpsertResult(sid=new_sid, is_created=True)

    async def refresh_session_if_exists(self, sid: str | None) -> bool:
        if sid is None:
            return False

        return await self._session_store.refresh_session(sid)

    async def get_session(self, sid: str | None) -> SessionData | None:
        if sid is None:
            return None

        return await self._session_store.get_session(sid)

    async def delete_session(self, sid: str | None) -> None:
        if sid is None:
            return

        await self._session_store.delete_session(sid)

    async def create_authenticated_session(
        self,
        user_id: str,
    ) -> SessionUpsertResult:
        new_sid = await self._create_new_session(user_id=user_id)
        return SessionUpsertResult(sid=new_sid, is_created=True)

    async def attach_user_to_session_or_create(
        self,
        sid: str | None,
        user_id: str,
    ) -> SessionUpsertResult:
        if sid is not None:
            attached = await self._session_store.set_user_id(sid, user_id)
            if attached:
                return SessionUpsertResult(sid=sid, is_created=False)

        new_sid = await self._create_new_session(user_id=user_id)
        return SessionUpsertResult(sid=new_sid, is_created=True)

    async def _create_new_session(self, user_id: str | None = None) -> str:
        for _ in range(self._max_attempts):
            sid = generate_sid()
            created = await self._session_store.create_session(
                sid,
                user_id=user_id,
            )
            if created:
                return sid

        raise RuntimeError("не получилось создать сессию")
