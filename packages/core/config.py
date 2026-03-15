"""Environment configuration for CloudOpt."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CLOUDOPT_",
        case_sensitive=False,
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://cloudopt:cloudopt@localhost:5432/cloudopt"
    database_url_sync: str = "postgresql://cloudopt:cloudopt@localhost:5432/cloudopt"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AWS (placeholders)
    aws_region: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # AI (placeholders)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
