"""FastAPI application. Run from `backend/`: `uvicorn app.main:app --reload --env-file ../.env`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import llm
from app.auth import TokenVerifier
from app.catalog import Catalog
from app.config import Settings, get_settings
from app.db import open_pool
from app.models.catalog import Health
from app.routers import catalog, chat, community, me


def create_app(
    settings: Settings | None = None,
    verifier: TokenVerifier | None = None,
    model_client: Any | None = None,
) -> FastAPI:
    """`verifier` replaces the token check built from SUPABASE_URL (tests use their own keys);
    `model_client` replaces the Gemini client built from GEMINI_API_KEY (tests use a fake)."""
    settings = settings or get_settings()
    if verifier is None and settings.supabase_url:
        verifier = TokenVerifier(settings.supabase_url)
    if model_client is None and settings.gemini_api_key:
        model_client = llm.make_client(settings.gemini_api_key, interactive=True)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.catalog = Catalog.load(settings.mais_data_dir)
        # without SUPABASE_URL nobody can log in; endpoints that need a user answer 503
        app.state.auth = verifier
        # without GEMINI_API_KEY /ask gives the placeholder answer (development, CI)
        app.state.model = model_client
        # without DATABASE_URL the app still serves the catalogue (from the JSON snapshot)
        app.state.db = open_pool(settings.database_url) if settings.database_url else None
        try:
            yield
        finally:
            if app.state.db is not None:
                app.state.db.close()

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
    app.include_router(me.router)
    app.include_router(chat.router)
    app.include_router(community.router)
    return app


app = create_app()
