from collections.abc import Callable, Iterator
import os
import uuid

# Make application import deterministic even when the host shell defines a
# non-boolean DEBUG variable for unrelated tooling.
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.models import User
from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.professionals.constants import ROLE_SEED_DATA
from app.professionals.models import ProfessionalRole


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_name="HealthLink Test",
        app_env="test",
        debug=False,
        database_url="postgresql://healthlink:healthlink@localhost:5432/healthlink_test",
        frontend_url="http://localhost:3000",
        jwt_secret_key="test-secret-key-with-at-least-thirty-two-characters",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )


@pytest.fixture
def db_engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    with Session(db_engine, expire_on_commit=False) as session:
        session.add_all(
            ProfessionalRole(
                code=code.value,
                name=name,
                description=description,
            )
            for code, name, description in ROLE_SEED_DATA
        )
        session.commit()
        yield session


@pytest.fixture
def user_factory(db_session: Session) -> Callable[..., User]:
    def create_user(
        *,
        email: str | None = None,
        is_active: bool = True,
    ) -> User:
        unique_value = uuid.uuid4().hex
        user = User(
            email=email or f"user-{unique_value}@example.com",
            password_hash="phase-1-test-password-hash",
            first_name="Test",
            last_name="User",
            is_active=is_active,
        )
        db_session.add(user)
        db_session.commit()
        return user

    return create_user


@pytest.fixture
def client(test_settings: Settings, db_session: Session) -> Iterator[TestClient]:
    application = create_app(test_settings)

    def override_get_db() -> Iterator[Session]:
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    with TestClient(application) as test_client:
        yield test_client
