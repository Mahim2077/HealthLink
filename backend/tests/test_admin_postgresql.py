import os
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.admins.models import AdminAccount, AdminActionLog
from app.admins.provisioning import create_trusted_admin
from app.auth.models import AuthSession, User
from app.core.config import Settings
from app.core.security import REFRESH_TOKEN_COOKIE_NAME
from app.db.session import create_database_engine, get_db
from app.main import create_app


POSTGRES_TEST_DATABASE_URL = os.getenv("HEALTHLINK_TEST_DATABASE_URL")


def _cleanup(engine, user_ids: list[uuid.UUID]) -> None:
    if not user_ids:
        return
    with engine.begin() as connection:
        connection.execute(
            delete(AdminActionLog).where(
                (AdminActionLog.admin_user_id.in_(user_ids))
                | (AdminActionLog.target_user_id.in_(user_ids))
            )
        )
        connection.execute(delete(AdminAccount).where(AdminAccount.user_id.in_(user_ids)))
        connection.execute(delete(AuthSession).where(AuthSession.user_id.in_(user_ids)))
        connection.execute(delete(User).where(User.id.in_(user_ids)))


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for admin PostgreSQL coverage",
)
def test_postgresql_admin_constraints_defaults_foreign_keys_and_timezones() -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    user_ids = [uuid.uuid4(), uuid.uuid4()]
    try:
        with Session(engine, expire_on_commit=False) as session:
            session.add_all(
                User(
                    id=user_id,
                    email=f"admin-constraint-{user_id.hex}@example.com",
                    password_hash="constraint-hash",
                    first_name="Admin",
                    last_name="Constraint",
                )
                for user_id in user_ids
            )
            session.commit()
            admin = AdminAccount(user_id=user_ids[0])
            session.add(admin)
            session.commit()
            session.refresh(admin)
            assert admin.is_active is True
            assert admin.is_super_admin is False
            assert admin.created_at.tzinfo is not None
            log = AdminActionLog(
                admin_user_id=user_ids[0],
                action_type="TEST_ADMIN_ACTION",
                target_user_id=user_ids[1],
                target_resource_type="test_resource",
                target_resource_id=uuid.uuid4(),
                reason="Constraint coverage",
            )
            session.add(log)
            session.commit()
            session.refresh(log)
            assert log.created_at.tzinfo is not None

        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(AdminAccount(user_id=user_ids[0]))
                session.commit()
        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(AdminAccount(user_id=uuid.uuid4()))
                session.commit()
        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(
                    AdminActionLog(
                        admin_user_id=uuid.uuid4(),
                        action_type="INVALID_ADMIN",
                    )
                )
                session.commit()
    finally:
        _cleanup(engine, user_ids)
        engine.dispose()


@pytest.mark.skipif(
    not POSTGRES_TEST_DATABASE_URL,
    reason="HEALTHLINK_TEST_DATABASE_URL is required for admin PostgreSQL coverage",
)
def test_live_postgresql_trusted_admin_login_me_and_inactive_denial(
    test_settings: Settings,
) -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    suffix = uuid.uuid4().hex
    email = f"live-admin-{suffix}@example.com"
    application = create_app(test_settings)
    user_ids: list[uuid.UUID] = []

    def postgres_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    application.dependency_overrides[get_db] = postgres_db
    try:
        with Session(engine, expire_on_commit=False) as session:
            provisioned = create_trusted_admin(
                session,
                email=email,
                password="LiveAdminPassword123!",
                first_name="Live",
                last_name="Administrator",
                is_super_admin=True,
            )
            user_ids.append(provisioned.user.id)

        with TestClient(application) as client:
            login = client.post(
                "/api/v1/auth/admin/login",
                json={"email": email, "password": "LiveAdminPassword123!"},
            )
            assert login.status_code == 200
            assert login.json()["portal"] == "ADMIN"
            assert REFRESH_TOKEN_COOKIE_NAME in login.cookies
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            me = client.get("/api/v1/admin/me", headers=headers)
            assert me.status_code == 200
            assert me.json()["email"] == email
            assert me.json()["is_super_admin"] is True

            with Session(engine) as session:
                admin = session.scalar(
                    select(AdminAccount).where(AdminAccount.user_id == user_ids[0])
                )
                admin.is_active = False
                session.commit()
            denied = client.get("/api/v1/admin/me", headers=headers)
            assert denied.status_code == 403
            denied_login = client.post(
                "/api/v1/auth/admin/login",
                json={"email": email, "password": "LiveAdminPassword123!"},
            )
            assert denied_login.status_code == 401
            assert denied_login.json() == {"detail": "Invalid email or password."}
    finally:
        _cleanup(engine, user_ids)
        engine.dispose()
