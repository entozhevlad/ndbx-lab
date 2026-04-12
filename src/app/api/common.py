from collections.abc import Mapping
from datetime import datetime

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

from app.session.types import SessionData
from app.user_session import get_request_sid, set_session_cookie


class InvalidFieldError(ValueError):
    def __init__(self, field_name: str) -> None:
        super().__init__(field_name)
        self.field_name = field_name


class InvalidParameterError(ValueError):
    def __init__(self, field_name: str) -> None:
        super().__init__(field_name)
        self.field_name = field_name


async def parse_json_body(request: Request) -> Mapping[str, object]:
    try:
        payload = await request.json()
    except ValueError:
        return {}

    if not isinstance(payload, dict):
        return {}

    return payload


def get_required_string_field(
    payload: Mapping[str, object],
    field_name: str,
) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or value.strip() == "":
        raise InvalidFieldError(field_name)

    return value


def get_required_rfc3339_field(
    payload: Mapping[str, object],
    field_name: str,
) -> tuple[str, datetime]:
    value = get_required_string_field(payload, field_name)
    parsed = _parse_rfc3339(value, field_name)
    return parsed.isoformat(), parsed


def parse_uint_parameter(value: str, field_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise InvalidParameterError(field_name) from exc

    if parsed < 0:
        raise InvalidParameterError(field_name)

    return parsed


def message_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"message": message},
    )


def invalid_field_response(field_name: str) -> JSONResponse:
    return message_response(
        status.HTTP_400_BAD_REQUEST,
        f'invalid "{field_name}" field',
    )


def invalid_parameter_response(field_name: str) -> JSONResponse:
    return message_response(
        status.HTTP_400_BAD_REQUEST,
        f'invalid "{field_name}" parameter',
    )


def set_response_session_cookie(
    request: Request,
    response: Response,
    sid: str,
) -> None:
    set_session_cookie(
        response,
        sid,
        request.app.state.settings.app_user_session_ttl,
    )


async def refresh_request_session(request: Request) -> str | None:
    sid = get_request_sid(request)
    if sid is None:
        return None

    refreshed = await request.app.state.session_module.service.refresh_session_if_exists(
        sid
    )
    if not refreshed:
        return None

    return sid


async def refresh_request_session_cookie(
    request: Request,
    response: Response,
) -> None:
    sid = await refresh_request_session(request)
    if sid is not None:
        set_response_session_cookie(request, response, sid)


async def get_existing_session(request: Request) -> SessionData | None:
    return await request.app.state.session_module.service.get_session(
        get_request_sid(request)
    )


def _parse_rfc3339(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidFieldError(field_name) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InvalidFieldError(field_name)

    return parsed
