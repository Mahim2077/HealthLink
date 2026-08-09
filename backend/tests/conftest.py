from collections.abc import Iterator
import os

# Make application import deterministic even when the host shell defines a
# non-boolean DEBUG variable for unrelated tooling.
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_name="HealthLink Test",
        app_env="test",
        debug=False,
        database_url="postgresql://healthlink:healthlink@localhost:5432/healthlink_test",
        frontend_url="http://localhost:3000",
    )


@pytest.fixture
def client(test_settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(test_settings)) as test_client:
        yield test_client
