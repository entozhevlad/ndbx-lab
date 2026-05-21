import asyncio

import bcrypt
from pymongo.errors import DuplicateKeyError

from app.users.store import UserStore


class UserAlreadyExistsError(Exception):
    pass


class UserService:
    def __init__(self, user_store: UserStore) -> None:
        self._user_store = user_store

    async def register_user(
        self,
        full_name: str,
        username: str,
        password: str,
    ) -> str:
        password_hash = await asyncio.to_thread(_hash_password, password)

        try:
            return await self._user_store.create_user(
                full_name=full_name,
                username=username,
                password_hash=password_hash,
            )
        except DuplicateKeyError as exc:
            raise UserAlreadyExistsError from exc

    async def authenticate(self, username: str, password: str) -> str | None:
        user = await self._user_store.get_user_by_username(username)
        if user is None:
            return None

        password_hash = user.get("password_hash")
        user_id = user.get("_id")

        if not isinstance(password_hash, str) or user_id is None:
            return None

        matches = await asyncio.to_thread(
            _password_matches,
            password,
            password_hash,
        )
        if not matches:
            return None

        return str(user_id)

    async def get_user_id_by_username(self, username: str) -> str | None:
        user = await self._user_store.get_user_by_username(username)
        if user is None:
            return None

        user_id = user.get("_id")
        if user_id is None:
            return None

        return str(user_id)

    async def get_public_user(self, user_id: str) -> dict[str, object] | None:
        user = await self._user_store.get_public_user_by_id(user_id)
        if user is None:
            return None

        return self._serialize_user(user)

    async def list_users(
        self,
        name: str,
        user_id: str | None,
        limit: int | None,
        offset: int,
    ) -> list[dict[str, object]]:
        users = await self._user_store.list_public_users(
            name=name,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        return [self._serialize_user(user) for user in users]

    @staticmethod
    def _serialize_user(user: dict[str, object]) -> dict[str, object]:
        return {
            "id": str(user.get("_id", "")),
            "full_name": _get_string(user.get("full_name")),
            "username": _get_string(user.get("username")),
        }


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


def _password_matches(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def _get_string(value: object) -> str:
    return value if isinstance(value, str) else ""
