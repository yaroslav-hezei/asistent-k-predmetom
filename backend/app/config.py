"""Runtime settings, read from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAIS_DATA_DIR = REPO_ROOT / "data" / "mais" / "2026-27"
DEFAULT_FRONTEND_ORIGINS = "http://localhost:3000"


@dataclass(frozen=True)
class Settings:
    mais_data_dir: Path
    frontend_origins: list[str]
    database_url: str | None = None
    supabase_url: str | None = None
    gemini_api_key: str | None = None


def get_settings() -> Settings:
    """MAIS_DATA_DIR: MAIS snapshot folder. FRONTEND_ORIGINS: comma-separated CORS origins.
    DATABASE_URL: Postgres connection string; without it the app runs without a database.
    SUPABASE_URL: project URL, used to verify login tokens; without it nobody can log in.
    GEMINI_API_KEY: the answering model; without it /ask gives the placeholder answer."""
    data_dir = os.environ.get("MAIS_DATA_DIR")
    origins = os.environ.get("FRONTEND_ORIGINS", DEFAULT_FRONTEND_ORIGINS)
    return Settings(
        mais_data_dir=Path(data_dir) if data_dir else DEFAULT_MAIS_DATA_DIR,
        frontend_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        database_url=os.environ.get("DATABASE_URL") or None,
        supabase_url=os.environ.get("SUPABASE_URL") or None,
        gemini_api_key=os.environ.get("GEMINI_API_KEY") or None,
    )
