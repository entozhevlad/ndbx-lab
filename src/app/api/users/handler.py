from fastapi import APIRouter, Request, Response, status

from app.api.common import (
    InvalidFieldError,
    get_required_string_field,
    invalid_field_response,
    message_response,
    parse_json_body,
    refresh_request_session,
    set_response_session_cookie,
)
from app.users.service import UserAlreadyExistsError

users_router = APIRouter()


@users_router.post("/users")
async def create_user(request: Request) -> Response:
    payload = await parse_json_body(request)

    try:
        full_name = get_required_string_field(payload, "full_name")
        username = get_required_string_field(payload, "username")
        password = get_required_string_field(payload, "password")
    except InvalidFieldError as exc:
        error_response = invalid_field_response(exc.field_name)
        sid = await refresh_request_session(request)
        if sid is not None:
            set_response_session_cookie(request, error_response, sid)
        return error_response

    try:
        user_id = await request.app.state.user_service.register_user(
            full_name=full_name,
            username=username,
            password=password,
        )
    except UserAlreadyExistsError:
        error_response = message_response(
            status.HTTP_409_CONFLICT,
            "user already exists",
        )
        sid = await refresh_request_session(request)
        if sid is not None:
            set_response_session_cookie(request, error_response, sid)
        return error_response

    session_result = (
        await request.app.state.session_module.service.create_authenticated_session(
            user_id
        )
    )

    created_response = Response(status_code=status.HTTP_201_CREATED)
    set_response_session_cookie(request, created_response, session_result.sid)
    return created_response
