from __future__ import annotations

from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    API_V1_PREFIX: str = "/api"

    # Supabase Postgres connection string
    SUPABASE_DB_URL: str = Field(..., description="SQLAlchemy async database URL")

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "o4-mini"

    # Tavily
    TAVILY_API_KEY: str
    TAVILY_MAX_RESULTS: int = 6

    # Scraping
    FIRECRAWL_API_KEY: Optional[str] = None

    # Networking
    REQUEST_TIMEOUT_S: int = 20

    # App behavior
    ENV: Literal["local", "dev", "prod"] = "local"


settings = Settings()
