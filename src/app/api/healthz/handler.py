from fastapi import APIRouter, Request, Response

from app.user_session import COOKIE_NAME, is_valid_sid, set_session_cookie

health_router = APIRouter()


@health_router.get("/health")
async def health_check(request: Request, response: Response):
    sid = request.cookies.get(COOKIE_NAME)

    if sid and is_valid_sid(sid):
        ttl_seconds = request.app.state.settings.app_user_session_ttl
        set_session_cookie(response, sid, ttl_seconds)

    return {"status": "ok"}
