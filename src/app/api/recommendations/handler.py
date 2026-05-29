from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.common import (get_existing_session,
                            refresh_request_session_cookie,
                            set_response_session_cookie)
from app.recommendations.service import RecommendationService

recommendations_router = APIRouter()


@recommendations_router.get("/recommendations")
async def list_recommendations(request: Request) -> Response:
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

    recommendation_service: RecommendationService = (
        request.app.state.recommendation_service
    )
    events = await recommendation_service.get_recommendations(session.user_id)

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"events": events},
    )
    set_response_session_cookie(request, response, session.sid)
    return response
