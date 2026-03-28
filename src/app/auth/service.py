from app.session.service import SessionService
from app.session.types import SessionUpsertResult
from app.users.service import UserService


class InvalidCredentialsError(Exception):
    pass


class AuthService:
    def __init__(
        self,
        user_service: UserService,
        session_service: SessionService,
    ) -> None:
        self._user_service = user_service
        self._session_service = session_service

    async def login(
        self,
        sid: str | None,
        username: str,
        password: str,
    ) -> SessionUpsertResult:
        user_id = await self._user_service.authenticate(username, password)
        if user_id is None:
            raise InvalidCredentialsError

        return await self._session_service.attach_user_to_session_or_create(
            sid=sid,
            user_id=user_id,
        )

    async def logout(self, sid: str | None) -> None:
        await self._session_service.delete_session(sid)
