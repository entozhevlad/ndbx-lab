import os

import uvicorn

from app.routers import all_routers
from app.service import create_app

app = create_app("Welcome to My FastAPI App")
for router in all_routers:
    app.include_router(router)

host = os.environ["APP_HOST"]
port = int(os.environ["APP_PORT"])

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
