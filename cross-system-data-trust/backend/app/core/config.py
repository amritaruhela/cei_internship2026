"""Application configuration loaded from environment variables."""
from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # API
    api_v1_str: str = "/api/v1"
    project_name: str = "DataTrust"
    secret_key: str = "CHANGE_THIS_IN_PRODUCTION_super_secret_key_for_jwt_signing"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Database
    database_url: str = "postgresql+asyncpg://datatrust:datatrust_pass@localhost:5432/datatrust"
    postgres_user: str = "datatrust"
    postgres_password: str = "datatrust_pass"
    postgres_db: str = "datatrust"

    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [o.strip() for o in v.split(",")]
        return v

    # Environment
    environment: str = "development"
    log_level: str = "INFO"

    # Data paths
    data_dir: str = "../data"
    raw_dir: str = "../data/raw"
    bronze_dir: str = "../data/bronze"
    silver_dir: str = "../data/silver"
    gold_dir: str = "../data/gold"
    generated_dir: str = "../data/generated"


settings = Settings()
