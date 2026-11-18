"""FastAPI application. Run from `backend/`: `uvicorn app.main:app --reload`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.catalog import Catalog
from app.config import Settings, get_settings
from app.models.catalog import Health
from app.routers import catalog


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.catalog = Catalog.load(settings.mais_data_dir)
        yield

    app = FastAPI(title="Asistent k predmetom API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"], summary="Liveness check")
    def health() -> Health:
        return Health(status="ok")

    app.include_router(catalog.router)
    return app


app = create_app()
