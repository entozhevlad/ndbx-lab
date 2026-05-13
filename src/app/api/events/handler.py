from collections.abc import Mapping

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.common import (
    InvalidFieldError,
    get_existing_session,
    get_optional_string_field,
    get_required_rfc3339_field,
    get_required_string_field,
    include_has,
    invalid_field_response,
    message_response,
    parse_json_body,
    parse_non_blank_parameter,
    parse_object_id_parameter,
    parse_uint_parameter,
    parse_yyyymmdd_parameter,
    refresh_request_session_cookie,
    set_response_session_cookie,
)
from app.api.schemas import EventCreatedResponse, EventListResponse, EventResponse
from app.events.service import EVENT_CATEGORIES, EventAlreadyExistsError
from app.reactions.service import ReactionService
from app.reviews.service import ReviewService
from app.user_session import get_request_sid

INCLUDE_REACTIONS = "reactions"
INCLUDE_REVIEWS = "reviews"

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
        event_id = (
            parse_object_id_parameter(params["id"], "id")
            if "id" in params
            else None
        )
        category = (
            _parse_event_category_parameter(params["category"])
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
        username = (
            parse_non_blank_parameter(params["user"], "user")
            if "user" in params
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
        _set_request_session_cookie_if_present(request, response)
        return response

    created_by = None
    if username is not None:
        created_by = await request.app.state.user_service.get_user_id_by_username(
            username
        )
        if created_by is None:
            response = JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "events": [],
                    "count": 0,
                },
            )
            _set_request_session_cookie_if_present(request, response)
            return response

    events = await request.app.state.event_service.list_events(
        title=title,
        event_id=event_id,
        category=category,
        price_from=price_from,
        price_to=price_to,
        city=city,
        date_from=date_from,
        date_to=date_to,
        created_by=created_by,
        limit=limit,
        offset=offset,
    )

    if include_has(request, INCLUDE_REACTIONS):
        await attach_reactions(
            request.app.state.reaction_service,
            events,
        )

    if include_has(request, INCLUDE_REVIEWS):
        await attach_reviews(
            request.app.state.review_service,
            events,
        )

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "events": events,
            "count": len(events),
        },
    )
    _set_request_session_cookie_if_present(request, response)
    return response


@events_router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(request: Request, event_id: str) -> Response:
    event = await request.app.state.event_service.get_event(event_id)
    if event is None:
        response = message_response(
            status.HTTP_404_NOT_FOUND,
            "Not found",
        )
        _set_request_session_cookie_if_present(request, response)
        return response

    if include_has(request, INCLUDE_REACTIONS):
        await attach_reactions(
            request.app.state.reaction_service,
            [event],
        )

    if include_has(request, INCLUDE_REVIEWS):
        await attach_reviews(
            request.app.state.review_service,
            [event],
        )

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=event,
    )
    _set_request_session_cookie_if_present(request, response)
    return response


@events_router.post(
    "/events/{event_id}/like",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def like_event(request: Request, event_id: str) -> Response:
    return await _handle_reaction(request, event_id, like=True)


@events_router.post(
    "/events/{event_id}/dislike",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def dislike_event(request: Request, event_id: str) -> Response:
    return await _handle_reaction(request, event_id, like=False)


async def _handle_reaction(
    request: Request,
    event_id: str,
    like: bool,
) -> Response:
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

    reaction_service: ReactionService = request.app.state.reaction_service
    if like:
        ok = await reaction_service.put_like(event_id, session.user_id)
    else:
        ok = await reaction_service.put_dislike(event_id, session.user_id)

    if not ok:
        response = message_response(
            status.HTTP_404_NOT_FOUND,
            "Event not found",
        )
        set_response_session_cookie(request, response, session.sid)
        return response

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    set_response_session_cookie(request, response, session.sid)
    return response


async def attach_reactions(
    reaction_service: ReactionService,
    events: list[dict[str, object]],
) -> None:
    titles: list[str] = []
    for event in events:
        title = event.get("title")
        if isinstance(title, str) and title != "":
            titles.append(title)

    counts = await reaction_service.counts_for_titles(titles)

    for event in events:
        title = event.get("title")
        likes, dislikes = 0, 0
        if isinstance(title, str) and title in counts:
            likes, dislikes = counts[title]
        event["reactions"] = {"likes": likes, "dislikes": dislikes}


async def attach_reviews(
    review_service: ReviewService,
    events: list[dict[str, object]],
) -> None:
    titles: list[str] = []
    for event in events:
        title = event.get("title")
        if isinstance(title, str) and title != "":
            titles.append(title)

    aggregates = await review_service.aggregates_for_titles(titles)

    for event in events:
        title = event.get("title")
        count, rating = 0, 0.0
        if isinstance(title, str) and title in aggregates:
            count, rating = aggregates[title]
        event["reviews"] = {
            "count": count,
            "rating": round(rating, 1),
        }


@events_router.patch("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_event(request: Request, event_id: str) -> Response:
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
        category = _parse_patch_category(payload)
        price = _parse_patch_price(payload)
        city, clear_city = _parse_patch_city(payload)
    except InvalidFieldError as exc:
        response = invalid_field_response(exc.field_name)
        set_response_session_cookie(request, response, session.sid)
        return response

    updated = await request.app.state.event_service.update_event(
        event_id=event_id,
        organizer_id=session.user_id,
        category=category,
        price=price,
        city=city,
        clear_city=clear_city,
    )
    if not updated:
        response = message_response(
            status.HTTP_404_NOT_FOUND,
            "Event not found",
        )
        set_response_session_cookie(request, response, session.sid)
        return response

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    set_response_session_cookie(request, response, session.sid)
    return response


def _parse_event_category_parameter(value: str) -> str:
    return _validate_event_category(
        parse_non_blank_parameter(value, "category"),
        "category",
    )


def _parse_patch_category(payload: Mapping[str, object]) -> str | None:
    value = get_optional_string_field(payload, "category")
    if value is None:
        return None

    return _validate_event_category(value, "category")


def _parse_patch_price(payload: Mapping[str, object]) -> int | None:
    if "price" not in payload:
        return None

    value = payload.get("price")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidFieldError("price")

    return value


def _parse_patch_city(payload: Mapping[str, object]) -> tuple[str | None, bool]:
    value = get_optional_string_field(payload, "city")
    if value is None:
        return None, False

    if value == "":
        return None, True

    if value.strip() == "":
        raise InvalidFieldError("city")

    return value, False


def _validate_event_category(value: str, field_name: str) -> str:
    if value not in EVENT_CATEGORIES:
        raise InvalidFieldError(field_name)

    return value


def _set_request_session_cookie_if_present(
    request: Request,
    response: Response,
) -> None:
    sid = get_request_sid(request)
    if sid is not None:
        set_response_session_cookie(request, response, sid)
