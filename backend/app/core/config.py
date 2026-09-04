from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PositiveInt, field_validator
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

    # Phase 13 prescription PDFs use private local storage in development and
    # a private Vercel Blob store in production. The application always serves
    # the bytes through an authorized API route; raw storage keys never reach
    # the browser.
    prescription_storage_backend: Literal["local", "vercel_blob"] = Field(
        default="local",
        validation_alias="PRESCRIPTION_STORAGE_BACKEND",
    )
    prescription_storage_path: str = Field(
        default="",
        validation_alias="PRESCRIPTION_STORAGE_PATH",
    )
    blob_read_write_token: str = Field(
        default="",
        validation_alias="BLOB_READ_WRITE_TOKEN",
        repr=False,
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
        "jwt_secret_key",
        "blob_read_write_token",
    )
    @classmethod
    def strip_surrounding_whitespace(cls, value: str) -> str:
        return value.strip()

    @property
    def cors_origins(self) -> list[str]:
        return [self.frontend_url.rstrip("/")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
