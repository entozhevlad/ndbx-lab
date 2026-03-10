from fastapi import APIRouter, Request, Response, status

from app.user_session import COOKIE_NAME, is_valid_sid, set_session_cookie

session_router = APIRouter()


@session_router.post("/session")
async def create_or_update_session(request: Request) -> Response:
    settings = request.app.state.settings
    session_module = request.app.state.session_module

    raw_sid = request.cookies.get(COOKIE_NAME)
    sid = raw_sid if raw_sid and is_valid_sid(raw_sid) else None

    result = await session_module.service.create_or_refresh_session(sid)

    response = Response(
        status_code=(
            status.HTTP_201_CREATED if result.is_created else status.HTTP_200_OK
        )
    )
    set_session_cookie(response, result.sid, settings.app_user_session_ttl)

    return response
