import os

import uvicorn
from dotenv import load_dotenv

from app.routers import all_routers
from app.service import create_app

load_dotenv(".env.local")

app = create_app("Welcome to My FastAPI App")
for router in all_routers:
    app.include_router(router)

host = os.getenv("APP_HOST", "0.0.0.0")
port = int(os.getenv("APP_PORT", "8000"))

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
