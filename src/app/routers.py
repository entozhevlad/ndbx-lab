from app.api.healthz.handler import health_router
from app.api.session.handler import session_router

all_routers = [health_router, session_router]