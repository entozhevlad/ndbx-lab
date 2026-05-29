from collections.abc import Mapping

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.common import (InvalidFieldError, InvalidParameterError,
                            get_existing_session, invalid_field_response,
                            invalid_parameter_response, message_response,
                            parse_json_body, parse_uint_parameter,
                            refresh_request_session_cookie,
                            set_response_session_cookie)
from app.reviews.service import (EventNotFoundError, ReviewAlreadyExistsError,
                                 ReviewNotFoundError, ReviewService)
from app.reviews.store import Review
from app.user_session import get_request_sid

MAX_COMMENT_LENGTH = 300
MIN_RATING = 1
MAX_RATING = 5

reviews_router = APIRouter()


@reviews_router.post(
    "/events/{event_id}/reviews",
    status_code=status.HTTP_201_CREATED,
)
async def create_review(request: Request, event_id: str) -> Response:
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
        rating = _parse_required_rating(payload)
        comment = _parse_required_comment(payload)
    except InvalidFieldError as exc:
        response = invalid_field_response(exc.field_name)
        set_response_session_cookie(request, response, session.sid)
        return response

    review_service: ReviewService = request.app.state.review_service
    try:
        review_id = await review_service.create_review(
            event_id=event_id,
            user_id=session.user_id,
            rating=rating,
            comment=comment,
        )
    except EventNotFoundError:
        response = message_response(
            status.HTTP_404_NOT_FOUND,
            "Event not found",
        )
        set_response_session_cookie(request, response, session.sid)
        return response
    except ReviewAlreadyExistsError:
        response = message_response(
            status.HTTP_409_CONFLICT,
            "Already exists",
        )
        set_response_session_cookie(request, response, session.sid)
        return response

    response = JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"id": review_id},
    )
    set_response_session_cookie(request, response, session.sid)
    return response


@reviews_router.get("/events/{event_id}/reviews")
async def list_reviews(request: Request, event_id: str) -> Response:
    params = request.query_params

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
        _set_request_session_cookie_if_present(request, response)
        return response

    review_service: ReviewService = request.app.state.review_service
    reviews = await review_service.list_reviews(
        event_id=event_id,
        limit=limit,
        offset=offset,
    )

    serialized = [_serialize_review(review) for review in reviews]
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "reviews": serialized,
            "count": len(serialized),
        },
    )
    _set_request_session_cookie_if_present(request, response)
    return response


@reviews_router.patch(
    "/events/{event_id}/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_review(
    request: Request,
    event_id: str,
    review_id: str,
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

    payload = await parse_json_body(request)

    try:
        rating = _parse_optional_rating(payload)
        comment = _parse_optional_comment(payload)
    except InvalidFieldError as exc:
        response = invalid_field_response(exc.field_name)
        set_response_session_cookie(request, response, session.sid)
        return response

    review_service: ReviewService = request.app.state.review_service
    try:
        await review_service.update_review(
            event_id=event_id,
            review_id=review_id,
            user_id=session.user_id,
            rating=rating,
            comment=comment,
        )
    except (EventNotFoundError, ReviewNotFoundError):
        response = message_response(
            status.HTTP_404_NOT_FOUND,
            "Event not found",
        )
        set_response_session_cookie(request, response, session.sid)
        return response

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    set_response_session_cookie(request, response, session.sid)
    return response


def _parse_required_rating(payload: Mapping[str, object]) -> int:
    if "rating" not in payload:
        raise InvalidFieldError("rating")
    return _validate_rating(payload.get("rating"))


def _parse_optional_rating(payload: Mapping[str, object]) -> int | None:
    if "rating" not in payload:
        return None
    return _validate_rating(payload.get("rating"))


def _validate_rating(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidFieldError("rating")
    if value < MIN_RATING or value > MAX_RATING:
        raise InvalidFieldError("rating")
    return value


def _parse_required_comment(payload: Mapping[str, object]) -> str:
    if "comment" not in payload:
        raise InvalidFieldError("comment")
    return _validate_comment(payload.get("comment"))


def _parse_optional_comment(payload: Mapping[str, object]) -> str | None:
    if "comment" not in payload:
        return None
    return _validate_comment(payload.get("comment"))


def _validate_comment(value: object) -> str:
    if not isinstance(value, str):
        raise InvalidFieldError("comment")
    if len(value) > MAX_COMMENT_LENGTH:
        raise InvalidFieldError("comment")
    return value


def _serialize_review(review: Review) -> dict[str, object]:
    return {
        "id": review.id,
        "event_id": review.event_id,
        "comment": review.comment,
        "rating": review.rating,
        "created_at": _format_dt(review.created_at),
        "created_by": review.created_by,
        "updated_at": _format_dt(review.updated_at),
    }


def _format_dt(value: object) -> str:
    if hasattr(value, "isoformat"):
        formatted = value.isoformat(timespec="seconds")
        return formatted.replace("+00:00", "Z")
    return ""


def _set_request_session_cookie_if_present(
    request: Request,
    response: Response,
) -> None:
    sid = get_request_sid(request)
    if sid is not None:
        set_response_session_cookie(request, response, sid)
