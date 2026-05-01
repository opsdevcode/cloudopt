"""Environment configuration for CloudOpt."""

from functools import lru_cache

from pydantic import field_validator
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
    # Comma-separated browser origins for CORS (e.g. Next.js dev). Empty = no CORS middleware.
    cors_origins: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://cloudopt:cloudopt@localhost:5432/cloudopt"
    database_url_sync: str = "postgresql://cloudopt:cloudopt@localhost:5432/cloudopt"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AWS (placeholders)
    aws_region: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    # Audit collectors (optional limits to bound worker runtime)
    audit_security_hub_max_findings: int = 500
    audit_config_max_rules: int = 200
    # CLI / integrations
    api_base_url: str = "http://127.0.0.1:8000"

    # AI: OpenAI-compatible API (vLLM, OpenAI, or other)
    # If llm_base_url is set, it takes precedence for chat/embeddings; else https://api.openai.com/v1
    # with openai_api_key.
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_chat_model: str = "Qwen/Qwen2.5-7B-Instruct"
    llm_embed_model: str = "BAAI/bge-m3"
    # Must match the embedding model output dimension and DB vector column (default: bge-m3 / many open models).
    embedding_dimensions: int = 1024
    # Legacy name still supported in code paths that check OpenAI directly
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Agent (Phase C): tool-calling loop in worker
    agent_tools_enabled: bool = True
    agent_max_tool_rounds: int = 6

    @field_validator("api_base_url", mode="before")
    @classmethod
    def _strip_api_base_url(cls, v: object) -> object:
        if isinstance(v, str):
            return v.rstrip("/")
        return v

    @field_validator(
        "llm_base_url", "llm_api_key", "openai_api_key", "anthropic_api_key", mode="before"
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        if v == "":
            return None
        return v


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
