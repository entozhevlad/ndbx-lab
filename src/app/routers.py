from app.api.auth.handler import auth_router
from app.api.events.handler import events_router
from app.api.healthz.handler import health_router
from app.api.reviews.handler import reviews_router
from app.api.session.handler import session_router
from app.api.users.handler import users_router

all_routers = [
    health_router,
    session_router,
    users_router,
    auth_router,
    events_router,
    reviews_router,
]
