"""Environment-driven application settings (pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration sourced from environment variables.

    All values have safe local-development defaults so the app boots with zero
    configuration. In production, set ``CORS_ORIGINS`` to the deployed frontend
    origin(s).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Digital Twin — Electrolux UAE Operations"
    app_env: str = "development"
    version: str = "1.0.0"

    # Comma-separated list of allowed CORS origins. Defaults cover local dev.
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Allow any *.vercel.app preview/production deployment via regex.
    cors_origin_regex: str = r"https://.*\.vercel\.app"

    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        """Accept a comma-separated string from the environment."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
