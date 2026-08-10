"""
eco-chat.uz — Application Settings
All configuration from environment variables. Never hardcode secrets.
"""
from __future__ import annotations

import json
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://ecochat:ecochat_pass@localhost:5432/ecochat_db"
    database_url_sync: str = "postgresql://ecochat:ecochat_pass@localhost:5432/ecochat_db"

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Telegram Bot (REQUIRED in production) ───────────────
    telegram_bot_token: str = ""

    # ── Security ─────────────────────────────────────────────
    secret_key: str = "CHANGE-THIS-IN-PRODUCTION"
    admin_secret: str = "CHANGE-THIS-IN-PRODUCTION"
    internal_api_secret: str = "CHANGE-THIS-IN-PRODUCTION"

    # ── Environment ──────────────────────────────────────────
    environment: str = "development"
    log_level: str = "INFO"
    tz: str = "Asia/Tashkent"

    # ── CORS ─────────────────────────────────────────────────
    corsorigins: str = '["http://localhost","http://localhost:80","http://127.0.0.1"]'

    # ── JWT ──────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours

    # ── Business Rules ───────────────────────────────────────
    question_timer_seconds: int = 30
    min_questions_per_topic: int = 15
    attempt2_min_wait_seconds: int = 600   # 10 minutes (hidden from user)
    max_attempts_per_topic: int = 2

    # ── Backend URL (for bot → API calls) ───────────────────
    backend_url: str = "http://localhost:8000"

    # ── Postgres (for backup scripts) ───────────────────────
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "ecochat_db"
    postgres_user: str = "ecochat"
    postgres_password: str = "ecochat_pass"

    @property
    def cors_origins_list(self) -> List[str]:
        try:
            parsed = json.loads(self.corsorigins)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return ["*"]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def bot_token_valid(self) -> bool:
        """Check if bot token looks valid (basic format check)."""
        t = self.telegram_bot_token
        return bool(t) and ":" in t and len(t) > 20


settings = Settings()
