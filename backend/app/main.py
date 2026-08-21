from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import router
from app.config import get_settings
from app.core import store
from app.core.watchdog import start as start_watch


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init()
    try:
        from app.rag.chat import reindex

        reindex()
    except Exception:
        pass
    try:
        from app.core.ocr import warmup

        warmup()
    except Exception:
        pass
    start_watch()
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="CUADREIQ", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[s.CORS_ORIGIN, "http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    return app


app = create_app()
