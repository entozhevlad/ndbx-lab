from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.common import (
    InvalidFieldError,
    InvalidParameterError,
    get_existing_session,
    get_required_rfc3339_field,
    get_required_string_field,
    invalid_field_response,
    invalid_parameter_response,
    message_response,
    parse_json_body,
    parse_uint_parameter,
    refresh_request_session_cookie,
    set_response_session_cookie,
)
from app.api.schemas import EventCreatedResponse, EventListResponse
from app.events.service import EventAlreadyExistsError
from app.user_session import get_request_sid

events_router = APIRouter()


@events_router.post(
    "/events",
    response_model=EventCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(request: Request) -> Response:
    session = await get_existing_session(request)
    if session is None or session.user_id is None:
        response = Response(status_code=status.HTTP_401_UNAUTHORIZED)
        await refresh_request_session_cookie(request, response)
        return response

    refreshed = await request.app.state.session_module.service.refresh_session_if_exists(
        session.sid
    )
    if not refreshed:
        response = Response(status_code=status.HTTP_401_UNAUTHORIZED)
        await refresh_request_session_cookie(request, response)
        return response

    payload = await parse_json_body(request)

    try:
        title = get_required_string_field(payload, "title")
        address = get_required_string_field(payload, "address")
        started_at, started_at_value = get_required_rfc3339_field(
            payload,
            "started_at",
        )
        finished_at, finished_at_value = get_required_rfc3339_field(
            payload,
            "finished_at",
        )
        description = get_required_string_field(payload, "description")
        if finished_at_value < started_at_value:
            raise InvalidFieldError("finished_at")
    except InvalidFieldError as exc:
        response = invalid_field_response(exc.field_name)
        set_response_session_cookie(request, response, session.sid)
        return response

    try:
        event_id = await request.app.state.event_service.create_event(
            title=title,
            address=address,
            started_at=started_at,
            finished_at=finished_at,
            description=description,
            user_id=session.user_id,
        )
    except EventAlreadyExistsError:
        response = message_response(
            status.HTTP_409_CONFLICT,
            "event already exists",
        )
        set_response_session_cookie(request, response, session.sid)
        return response

    response = JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"id": event_id},
    )
    set_response_session_cookie(request, response, session.sid)
    return response


@events_router.get("/events", response_model=EventListResponse)
async def list_events(request: Request) -> Response:
    params = request.query_params
    title = params.get("title", "")

    try:
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
    except InvalidParameterError as exc:
        response = invalid_parameter_response(exc.field_name)
        sid = get_request_sid(request)
        if sid is not None:
            set_response_session_cookie(request, response, sid)
        return response

    events = await request.app.state.event_service.list_events(
        title=title,
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
