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


def test_settings_repr_does_not_expose_credentials() -> None:
    database_url = "postgresql://private-user:private-password@example.invalid/private"
    jwt_secret = "private-jwt-secret-with-at-least-thirty-two-characters"
    settings = Settings(
        _env_file=None,
        database_url=database_url,
        jwt_secret_key=jwt_secret,
    )

    rendered_settings = repr(settings)

    assert database_url not in rendered_settings
    assert "private-password" not in rendered_settings
    assert jwt_secret not in rendered_settings


@pytest.mark.parametrize("provider", ["gemini", "groq"])
def test_ai_key_is_redacted_and_remote_provider_requires_it_when_enabled(provider) -> None:
    ai_key = "synthetic-private-ai-key"
    settings = Settings(
        _env_file=None,
        ai_enabled=True,
        ai_provider=provider,
        ai_api_key=ai_key,
    )

    assert ai_key not in repr(settings)
    with pytest.raises(ValidationError, match="AI_API_KEY"):
        Settings(
            _env_file=None,
            ai_enabled=True,
            ai_provider=provider,
            ai_api_key="",
        )


def test_groq_is_default_but_ai_and_record_transfer_stay_disabled(monkeypatch):
    for name in ("AI_PROVIDER", "AI_MODEL", "AI_ENABLED", "AI_RECORD_CONTEXT_ENABLED"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)
    assert settings.ai_provider == "groq"
    assert settings.ai_model == "qwen/qwen3.8-27b"
    assert not settings.ai_enabled
    assert not settings.ai_record_context_enabled


@pytest.mark.parametrize(
    ("provider", "model"),
    [("groq", "qwen/qwen3.8-27b"), ("gemini", "gemini-3.5-flash")],
)
def test_model_default_follows_provider_and_model_override_is_preserved(monkeypatch, provider, model):
    monkeypatch.delenv("AI_MODEL", raising=False)
    assert Settings(_env_file=None, ai_provider=provider).ai_model == model
    assert Settings(_env_file=None, ai_provider=provider, ai_model=" custom-model ").ai_model == "custom-model"


def test_record_context_cannot_be_enabled_without_ai() -> None:
    with pytest.raises(ValidationError, match="AI_RECORD_CONTEXT_ENABLED"):
        Settings(
            _env_file=None,
            ai_enabled=False,
            ai_record_context_enabled=True,
        )
