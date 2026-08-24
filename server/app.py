"""FastAPI assembly.

Routes only; business logic lives in the agent and tool packages.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.routes import router
from server.runtime import bus
from server.websocket import socket

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def create_app() -> FastAPI:

    app = FastAPI(title="ALICE", docs_url=None, redoc_url=None)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.websocket("/ws")(socket)

    @app.on_event("startup")
    async def bind_bus():
        import asyncio

        bus.bind(asyncio.get_running_loop())

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

    return app


app = create_app()
