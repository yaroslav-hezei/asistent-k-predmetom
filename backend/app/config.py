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


def get_settings() -> Settings:
    """MAIS_DATA_DIR: MAIS snapshot folder. FRONTEND_ORIGINS: comma-separated CORS origins."""
    data_dir = os.environ.get("MAIS_DATA_DIR")
    origins = os.environ.get("FRONTEND_ORIGINS", DEFAULT_FRONTEND_ORIGINS)
    return Settings(
        mais_data_dir=Path(data_dir) if data_dir else DEFAULT_MAIS_DATA_DIR,
        frontend_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
    )
