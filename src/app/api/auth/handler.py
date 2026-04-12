from fastapi import APIRouter, Request, Response, status

from app.api.common import (
    InvalidFieldError,
    get_existing_session,
    get_required_string_field,
    invalid_field_response,
    message_response,
    parse_json_body,
    refresh_request_session_cookie,
    set_response_session_cookie,
)
from app.auth.service import InvalidCredentialsError
from app.user_session import clear_session_cookie, get_request_sid

auth_router = APIRouter()


@auth_router.post("/auth/login")
async def login(request: Request) -> Response:
    payload = await parse_json_body(request)

    try:
        username = get_required_string_field(payload, "username")
        password = get_required_string_field(payload, "password")
    except InvalidFieldError as exc:
        response = invalid_field_response(exc.field_name)
        await refresh_request_session_cookie(request, response)
        return response

    try:
        session_result = await request.app.state.auth_service.login(
            sid=get_request_sid(request),
            username=username,
            password=password,
        )
    except InvalidCredentialsError:
        error_response = message_response(
            status.HTTP_401_UNAUTHORIZED,
            "invalid credentials",
        )
        await refresh_request_session_cookie(request, error_response)
        return error_response

    success_response = Response(status_code=status.HTTP_204_NO_CONTENT)
    set_response_session_cookie(request, success_response, session_result.sid)
    return success_response


@auth_router.post("/auth/logout")
async def logout(request: Request) -> Response:
    session = await get_existing_session(request)
    if session is None or session.user_id is None:
        unauthorized_response = Response(status_code=status.HTTP_401_UNAUTHORIZED)
        await refresh_request_session_cookie(request, unauthorized_response)
        return unauthorized_response

    await request.app.state.auth_service.logout(session.sid)

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response)
    return response
