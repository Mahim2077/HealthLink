from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PositiveInt, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="HealthLink", validation_alias="APP_NAME")
    app_env: Literal["development", "test", "staging", "production"] = Field(
        default="development",
        validation_alias="APP_ENV",
    )
    debug: bool = Field(default=False, validation_alias="DEBUG")
    cron_secret: str = Field(default="", validation_alias="CRON_SECRET", repr=False)
    database_url: str = Field(
        default="",
        validation_alias="DATABASE_URL",
        repr=False,
    )
    db_disable_prepared_statements: bool = Field(
        default=False,
        validation_alias="DB_DISABLE_PREPARED_STATEMENTS",
    )
    frontend_url: str = Field(
        default="http://localhost:3000",
        validation_alias="FRONTEND_URL",
    )
    geocoder_base_url: str = Field(
        default="https://nominatim.openstreetmap.org",
        validation_alias="GEOCODER_BASE_URL",
    )
    geocoder_user_agent: str = Field(
        default="HealthLink/0.1 (+https://healthlink-sd.vercel.app/)",
        validation_alias="GEOCODER_USER_AGENT",
    )
    jwt_secret_key: str = Field(
        default="",
        validation_alias="JWT_SECRET_KEY",
        repr=False,
    )
    jwt_algorithm: Literal["HS256"] = Field(
        default="HS256",
        validation_alias="JWT_ALGORITHM",
    )
    access_token_expire_minutes: PositiveInt = Field(
        default=30,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    refresh_token_expire_days: PositiveInt = Field(
        default=7,
        validation_alias="REFRESH_TOKEN_EXPIRE_DAYS",
    )
    ai_enabled: bool = Field(default=False, validation_alias="AI_ENABLED")
    ai_provider: Literal["mock", "gemini", "groq"] = Field(
        default="groq",
        validation_alias="AI_PROVIDER",
    )
    ai_api_key: str = Field(
        default="",
        validation_alias="AI_API_KEY",
        repr=False,
    )
    ai_model: str = Field(
        default="",
        validation_alias="AI_MODEL",
    )
    ai_record_context_enabled: bool = Field(
        default=False,
        validation_alias="AI_RECORD_CONTEXT_ENABLED",
    )
    ai_timeout_seconds: PositiveInt = Field(
        default=20,
        validation_alias="AI_TIMEOUT_SECONDS",
        le=60,
    )
    ai_max_input_characters: PositiveInt = Field(
        default=12_000,
        validation_alias="AI_MAX_INPUT_CHARACTERS",
        ge=2_000,
        le=50_000,
    )
    ai_max_context_records: PositiveInt = Field(
        default=10,
        validation_alias="AI_MAX_CONTEXT_RECORDS",
        le=25,
    )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug_mode(cls, value: object) -> object:
        # Some development shells define DEBUG=release globally. Treat the
        # conventional release/production modes as the safe, non-debug value.
        if isinstance(value, str) and value.strip().lower() in {
            "release",
            "production",
            "prod",
        }:
            return False
        return value

    @field_validator(
        "database_url",
        "frontend_url",
        "geocoder_base_url",
        "geocoder_user_agent",
        "jwt_secret_key",
        "ai_api_key",
        "ai_model",
    )
    @classmethod
    def strip_surrounding_whitespace(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_ai_configuration(self) -> "Settings":
        # A provider switch without AI_MODEL must not send a Gemini model ID to
        # Groq (or vice versa). Explicit model overrides remain replaceable.
        if not self.ai_model:
            self.ai_model = (
                "gemini-3.5-flash"
                if self.ai_provider == "gemini"
                else "qwen/qwen3.8-27b"
            )
        if self.ai_record_context_enabled and not self.ai_enabled:
            raise ValueError(
                "AI_RECORD_CONTEXT_ENABLED requires AI_ENABLED=true."
            )
        if self.ai_enabled and self.ai_provider != "mock" and not self.ai_api_key:
            raise ValueError(
                "AI_API_KEY is required when an external AI provider is enabled."
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [self.frontend_url.rstrip("/")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
