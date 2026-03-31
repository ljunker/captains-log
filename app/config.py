from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings:
    app_name = "Captain's Log"
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    sqlite_path = Path(os.getenv("SQLITE_PATH", BASE_DIR / "data" / "captains_log.db"))
    database_url = os.getenv("DATABASE_URL", f"sqlite:///{sqlite_path}")
    api_key = os.getenv("API_KEY")
    root_path = os.getenv("APP_ROOT_PATH", "").rstrip("/")


settings = Settings()
