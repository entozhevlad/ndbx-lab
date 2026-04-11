from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.common import (
    InvalidFieldError,
    get_required_string_field,
    invalid_field_response,
    message_response,
    parse_json_body,
    parse_non_blank_parameter,
    parse_object_id_parameter,
    parse_uint_parameter,
    parse_yyyymmdd_parameter,
    refresh_request_session,
    set_response_session_cookie,
)
from app.api.schemas import EventListResponse, UserListResponse, UserResponse
from app.events.service import EVENT_CATEGORIES
from app.user_session import get_request_sid
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


@users_router.get("/users", response_model=UserListResponse)
async def list_users(request: Request) -> Response:
    params = request.query_params
    name = params.get("name", "")

    try:
        user_id = (
            parse_object_id_parameter(params["id"], "id")
            if "id" in params
            else None
        )
        limit = (
            parse_uint_parameter(params["limit"], "limit")
            if "limit" in params
            else None
        )
        offset = (
            parse_uint_parameter(params["offset"], "offset")
            if "offset" in params
            else 0
        )
    except InvalidFieldError as exc:
        response = invalid_field_response(exc.field_name)
        sid = get_request_sid(request)
        if sid is not None:
            set_response_session_cookie(request, response, sid)
        return response

    users = await request.app.state.user_service.list_users(
        name=name,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "users": users,
            "count": len(users),
        },
    )

    sid = get_request_sid(request)
    if sid is not None:
        set_response_session_cookie(request, response, sid)

    return response


@users_router.get("/users/{user_id}/events", response_model=EventListResponse)
async def list_user_events(request: Request, user_id: str) -> Response:
    user = await request.app.state.user_service.get_public_user(user_id)
    if user is None:
        response = message_response(
            status.HTTP_404_NOT_FOUND,
            "User not found",
        )
        sid = get_request_sid(request)
        if sid is not None:
            set_response_session_cookie(request, response, sid)
        return response

    params = request.query_params
    title = params.get("title", "")

    try:
        category = (
            _parse_event_category(params["category"])
            if "category" in params
            else None
        )
        price_from = (
            parse_uint_parameter(params["price_from"], "price_from")
            if "price_from" in params
            else None
        )
        price_to = (
            parse_uint_parameter(params["price_to"], "price_to")
            if "price_to" in params
            else None
        )
        city = (
            parse_non_blank_parameter(params["city"], "city")
            if "city" in params
            else None
        )
        date_from = (
            parse_yyyymmdd_parameter(params["date_from"], "date_from")
            if "date_from" in params
            else None
        )
        date_to = (
            parse_yyyymmdd_parameter(params["date_to"], "date_to")
            if "date_to" in params
            else None
        )
        limit = (
            parse_uint_parameter(params["limit"], "limit")
            if "limit" in params
            else None
        )
        offset = (
            parse_uint_parameter(params["offset"], "offset")
            if "offset" in params
            else 0
        )
        if price_from is not None and price_to is not None and price_to < price_from:
            raise InvalidFieldError("price_to")
        if date_from is not None and date_to is not None and date_to < date_from:
            raise InvalidFieldError("date_to")
    except InvalidFieldError as exc:
        response = invalid_field_response(exc.field_name)
        sid = get_request_sid(request)
        if sid is not None:
            set_response_session_cookie(request, response, sid)
        return response

    events = await request.app.state.event_service.list_events(
        title=title,
        event_id=None,
        category=category,
        price_from=price_from,
        price_to=price_to,
        city=city,
        date_from=date_from,
        date_to=date_to,
        created_by=user_id,
        limit=limit,
        offset=offset,
    )

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "events": events,
            "count": len(events),
        },
    )

    sid = get_request_sid(request)
    if sid is not None:
        set_response_session_cookie(request, response, sid)

    return response


def _parse_event_category(value: str) -> str:
    parsed = parse_non_blank_parameter(value, "category")
    if parsed not in EVENT_CATEGORIES:
        raise InvalidFieldError("category")

    return parsed


@users_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(request: Request, user_id: str) -> Response:
    user = await request.app.state.user_service.get_public_user(user_id)
    if user is None:
        response = message_response(
            status.HTTP_404_NOT_FOUND,
            "Not found",
        )
        sid = get_request_sid(request)
        if sid is not None:
            set_response_session_cookie(request, response, sid)
        return response

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=user,
    )

    sid = get_request_sid(request)
    if sid is not None:
        set_response_session_cookie(request, response, sid)

    return response
