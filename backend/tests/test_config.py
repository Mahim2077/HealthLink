import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.db.session import normalize_database_url


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Configured HealthLink")
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.invalid/healthlink")
    monkeypatch.setenv("FRONTEND_URL", "https://healthlink.example/")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Configured HealthLink"
    assert settings.app_env == "staging"
    assert settings.debug is False
    assert settings.database_url == "postgresql://example.invalid/healthlink"
    assert settings.cors_origins == ["https://healthlink.example"]


def test_settings_reject_unknown_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="unknown")


def test_release_debug_mode_is_safely_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "release")

    settings = Settings(_env_file=None)

    assert settings.debug is False


def test_neon_style_postgresql_url_uses_psycopg_driver() -> None:
    url = normalize_database_url(
        "postgresql://healthlink:secret@example.invalid/healthlink?sslmode=require"
    )

    assert url.drivername == "postgresql+psycopg"
    assert url.query["sslmode"] == "require"


def test_database_url_is_required_only_when_database_is_used() -> None:
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        normalize_database_url("")
