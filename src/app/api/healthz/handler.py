from fastapi import APIRouter, Request, Response

from app.user_session import get_request_sid, set_session_cookie

health_router = APIRouter()


@health_router.get("/health")
async def health_check(request: Request, response: Response):
    sid = get_request_sid(request)
    if sid is not None:
        ttl_seconds = request.app.state.settings.app_user_session_ttl
        set_session_cookie(response, sid, ttl_seconds)

    return {"status": "ok"}
