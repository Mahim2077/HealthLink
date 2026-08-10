import os
import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.auth.models import AuthSession, User
from app.citizens.models import UserNationalIdentifier
from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import create_database_engine, get_db
from app.facilities.models import HealthcareFacility
from app.main import create_app
from app.professionals.models import HealthcareProfessionalProfile, ProfessionalRole, ProfessionalRoleRegistration


POSTGRES_TEST_DATABASE_URL = os.getenv("HEALTHLINK_TEST_DATABASE_URL")


@pytest.mark.skipif(not POSTGRES_TEST_DATABASE_URL, reason="HEALTHLINK_TEST_DATABASE_URL is required for professional login PostgreSQL coverage")
def test_postgresql_active_role_fk_and_live_multi_role_login(test_settings: Settings) -> None:
    assert POSTGRES_TEST_DATABASE_URL is not None
    engine = create_database_engine(POSTGRES_TEST_DATABASE_URL, poolclass=NullPool)
    suffix = uuid.uuid4().hex[:18]
    user_id: uuid.UUID | None = None; profile_id: uuid.UUID | None = None; facility_id: uuid.UUID | None = None
    app = create_app(test_settings)
    def postgres_db():
        with Session(engine, expire_on_commit=False) as session: yield session
    app.dependency_overrides[get_db] = postgres_db
    try:
        with Session(engine, expire_on_commit=False) as session:
            user = User(email=f"p7-{suffix}@example.com", password_hash=hash_password("ProfessionalPassword123!"), first_name="Live", last_name="Professional")
            session.add(user); session.flush(); user_id=user.id
            session.add(UserNationalIdentifier(user_id=user.id,nid_number=f"P7NID{suffix}"))
            profile=HealthcareProfessionalProfile(user_id=user.id); facility=HealthcareFacility(name=f"P7 Hospital {suffix}",facility_type="HOSPITAL",address="Dhaka")
            session.add_all([profile,facility]);session.flush();profile_id=profile.id;facility_id=facility.id
            registrations={}
            for code,status in [("DOCTOR","VERIFIED"),("LAB_TECHNICIAN","PENDING")]:
                role=session.scalar(select(ProfessionalRole).where(ProfessionalRole.code==code));assert role is not None
                registration=ProfessionalRoleRegistration(professional_id=profile.id,role_id=role.id,facility_id=facility.id if status=="VERIFIED" else None,facility_name_submitted=facility.name,designation=code,additional_info="P7 live",verification_status=status)
                session.add(registration);session.flush();registrations[code]=registration.id
            session.commit()
        with TestClient(app) as client:
            for code,status in [("DOCTOR","VERIFIED"),("LAB_TECHNICIAN","PENDING")]:
                response=client.post("/api/v1/auth/professional/login",json={"nid_number":f"P7NID{suffix}","password":"ProfessionalPassword123!","role_code":code})
                assert response.status_code==200; assert response.json()["verification_status"]==status
                claims=jwt.decode(response.json()["access_token"],test_settings.jwt_secret_key,algorithms=[test_settings.jwt_algorithm])
                assert claims["prrid"]==str(registrations[code])
                me=client.get("/api/v1/professionals/me",headers={"Authorization":f"Bearer {response.json()['access_token']}"})
                assert me.status_code==200;assert me.json()["role_code"]==code
        with pytest.raises(IntegrityError):
            with Session(engine) as session:
                session.add(AuthSession(user_id=user_id,portal="PROFESSIONAL",active_professional_role_registration_id=uuid.uuid4(),refresh_token_hash=uuid.uuid4().hex,expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc)))
                session.commit()
    finally:
        with engine.begin() as connection:
            if user_id is not None:
                connection.execute(delete(AuthSession).where(AuthSession.user_id==user_id))
            if profile_id is not None:
                connection.execute(delete(ProfessionalRoleRegistration).where(ProfessionalRoleRegistration.professional_id==profile_id))
                connection.execute(delete(HealthcareProfessionalProfile).where(HealthcareProfessionalProfile.id==profile_id))
            if user_id is not None:
                connection.execute(delete(UserNationalIdentifier).where(UserNationalIdentifier.user_id==user_id));connection.execute(delete(User).where(User.id==user_id))
            if facility_id is not None: connection.execute(delete(HealthcareFacility).where(HealthcareFacility.id==facility_id))
        engine.dispose()
