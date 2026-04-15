from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "LangGraph Agent System"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Server ───────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # ── Database ─────────────────────────────────────────────────
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "postgres"
    DATABASE_NAME: str = "agent_db"
    DATABASE_URL: str | None = None
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600

    # ── Redis ────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_USER_NAME: str = "default"
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_SSL: bool = True
    REDIS_URL: str | None = None

    # ── JWT / Auth ───────────────────────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Rate Limiting ────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── LLM Providers ───────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: Literal["openai", "anthropic", "gemini", "groq"] = "groq"
    # Groq: gpt-oss is strong for reasoning/chat; many IDs still emit invalid <function=...> XML for bind_tools.
    DEFAULT_MODEL_NAME: str = "openai/gpt-oss-120b"
    # Groq only: model for researcher plan_search (bind_tools). Llama 3.1 8B follows native tool_calls reliably.
    # Empty = use DEFAULT_MODEL_NAME for tools too (may hit tool_use_failed on some models).
    GROQ_TOOL_CALLING_MODEL: str = "llama-3.1-8b-instant"

    # ── Research Tools ────────────────────────────────────────
    TAVILY_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("TAVILY_API_KEY", "TAVILY_KEY"),
    )
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    PGVECTOR_COLLECTION: str = "knowledge_base"
    # Enable when PostgreSQL has the pgvector extension (e.g. pgvector/pgvector Docker image). Off by default for plain local Postgres.
    PGVECTOR_ENABLED: bool = False

    # ── Observability ────────────────────────────────────────────
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "langgraph-agents"
    OTEL_EXPORTER_ENDPOINT: str = ""

    # ── Celery ───────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    @field_validator("TAVILY_API_KEY", mode="before")
    @classmethod
    def _strip_tavily_api_key(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("GROQ_TOOL_CALLING_MODEL", mode="before")
    @classmethod
    def _strip_groq_tool_model(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Put `.env` before process env so repo config wins over stale OS/IDE variables.

        Default pydantic-settings order lets ``DEFAULT_LLM_PROVIDER`` etc. from the
        environment override ``.env``, which makes local edits look ignored.
        """
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )

    def get_database_url(self) -> str:
        """Build async SQLAlchemy URL from either DATABASE_URL or components."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    def get_database_sync_url(self) -> str:
        """Return sync psycopg-style URL for tools requiring non-async drivers."""
        return self.get_database_url().replace("+asyncpg", "")

    def get_redis_url(self) -> str:
        """Build Redis URL from either REDIS_URL or host credentials."""
        if self.REDIS_URL:
            return self.REDIS_URL
        scheme = "rediss" if self.REDIS_SSL else "redis"
        return (
            f"{scheme}://{self.REDIS_USER_NAME}:{self.REDIS_PASSWORD}"
            f"@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        )


def get_settings() -> Settings:
    """Fresh ``Settings()`` each call so ``.env`` edits apply without stale LRU cache."""
    return Settings()
