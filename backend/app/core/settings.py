from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def get_config_dir_root() -> Path:
    override = os.getenv("OPENHR_CONFIG_ROOT")
    return Path(override).expanduser().resolve() if override else PROJECT_ROOT


def get_cors_origins() -> list[str]:
    raw = os.getenv("OPENHR_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def get_api_prefix() -> str:
    return os.getenv("OPENHR_API_PREFIX", "/api/v1").rstrip("/")
