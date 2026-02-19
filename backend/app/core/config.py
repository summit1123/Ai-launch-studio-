"""Application settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Launch Studio API"
    api_prefix: str = "/api"
    environment: Literal["local", "dev", "prod"] = "local"
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.2"
    fal_key: str | None = None
    use_agent_sdk: bool = True
    db_path: str = "launch_studio.db"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
