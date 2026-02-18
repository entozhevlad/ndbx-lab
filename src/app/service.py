from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse


def create_app(root_message: str = "Welcome") -> FastAPI:
    app = FastAPI()

    @app.middleware("http")
    async def root_response(request: Request, call_next):
        if request.url.path == "/":
            return PlainTextResponse(root_message)
        return await call_next(request)

    return app
