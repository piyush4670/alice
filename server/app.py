"""FastAPI assembly.

Routes only; business logic lives in the agent and tool packages.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server import auth
from server.routes import router
from server.runtime import bus
from server.websocket import socket

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Open to everyone: the login screen itself, and health pings.
PUBLIC_PATHS = ("/api/auth", "/api/health")


def create_app() -> FastAPI:

    app = FastAPI(title="ALICE", docs_url=None, redoc_url=None)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def passcode_gate(request: Request, call_next):

        path = request.url.path

        if (
            auth.enabled()
            and path.startswith("/api")
            and not path.startswith(PUBLIC_PATHS)
            and not auth.authorised(request)
        ):
            return JSONResponse({"detail": "passcode required"}, status_code=401)

        return await call_next(request)

    app.include_router(router)
    app.websocket("/ws")(socket)

    @app.on_event("startup")
    async def bind_bus():
        import asyncio

        bus.bind(asyncio.get_running_loop())

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()
