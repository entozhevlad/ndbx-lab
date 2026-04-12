import uvicorn

from app.config import load_settings
from app.routers import all_routers
from app.service import create_app

app = create_app("Welcome to My FastAPI App")
for router in all_routers:
    app.include_router(router)

settings = load_settings()
host = settings.app_host
port = settings.app_port

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
