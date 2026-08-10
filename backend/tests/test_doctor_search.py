from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.admins.provisioning import create_trusted_admin
from app.auth.models import AuthSession
from app.facilities.models import HealthcareFacility
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)


CITIZEN_PASSWORD = "StrongPassword123!"
ADMIN_PASSWORD = "StrongAdminPassword123!"

CITIZEN_SEARCH_PATH = "/api/v1/doctors"
CITIZEN_PROFILE_PATH = "/api/v1/doctors/{doctor_user_id}"
PRACTICE_DAYS_PATH = "/api/v1/doctors/{doctor_user_id}/practice-days"


def register_citizen(client: TestClient) -> str:
    unique = uuid.uuid4().hex
    response = client.post(
        "/api/v1/auth/citizen/register",
        json={
            "email": f"citizen-{unique}@example.com",
            "password": CITIZEN_PASSWORD,
            "first_name": "Carla",
            "last_name": "Citizen",
            "date_of_birth": "1990-01-01",
            "gender": "FEMALE",
            "blood_group": "A+",
            "address": "Dhaka",
            "nid_number": f"NID-{unique[:24]}",
        },
    )
    assert response.status_code == 201, response.text
    login = client.post(
        "/api/v1/auth/citizen/login",
        json={
            "email": f"citizen-{unique}@example.com",
            "password": CITIZEN_PASSWORD,
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _admin_headers(client: TestClient, db_session) -> dict[str, str]:
    provisioned = create_trusted_admin(
        db_session,
        email=f"admin-{uuid.uuid4().hex}@example.com",
        password=ADMIN_PASSWORD,
        first_name="Review",
        last_name="Admin",
        is_super_admin=False,
    )
    response = client.post(
        "/api/v1/auth/admin/login",
        json={
            "email": provisioned.user.email,
            "password": ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _make_facility(db_session, *, name: str) -> HealthcareFacility:
    facility = HealthcareFacility(
        name=name,
        facility_type="HOSPITAL",
        registration_number=f"REG-{uuid.uuid4().hex[:8]}",
        address="HealthLink Avenue",
        phone="+8801700000000",
        email="facility@example.com",
        is_active=True,
    )
    db_session.add(facility)
    db_session.commit()
    db_session.refresh(facility)
    return facility


def _make_doctor(
    db_session,
    *,
    first_name: str,
    last_name: str,
    facility: HealthcareFacility,
    verified: bool = True,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a verified (or pending) doctor user, return (user_id, registration_id)."""

    from app.auth.models import User

    user = User(
        email=f"doctor-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="phase-1-test-password-hash",
        first_name=first_name,
        last_name=last_name,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = HealthcareProfessionalProfile(user_id=user.id)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    role = db_session.scalar(
        select(ProfessionalRole).where(
            ProfessionalRole.code == ProfessionalRoleCode.DOCTOR.value
        )
    )
    assert role is not None

    registration = ProfessionalRoleRegistration(
        professional_id=profile.id,
        role_id=role.id,
        facility_id=facility.id,
        facility_name_submitted=facility.name,
        designation="Consultant",
        verification_status=(
            VerificationStatus.VERIFIED.value
            if verified
            else VerificationStatus.PENDING.value
        ),
    )
    if verified:
        from datetime import datetime, timezone

        registration.verified_at = datetime.now(timezone.utc)
    db_session.add(registration)
    db_session.commit()
    db_session.refresh(registration)

    detail = DoctorRegistrationDetail(
        professional_role_registration_id=registration.id,
        bmdc_registration_number=f"BMDC-{uuid.uuid4().hex[:10]}",
    )
    db_session.add(detail)
    db_session.commit()

    return user.id, registration.id


def test_doctor_search_requires_authentication(client: TestClient) -> None:
    response = client.get(CITIZEN_SEARCH_PATH)
    assert response.status_code == 401


def test_doctor_search_requires_at_least_one_filter(client: TestClient) -> None:
    token = register_citizen(client)
    response = client.get(
        CITIZEN_SEARCH_PATH,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_doctor_search_filters_by_name_facility_and_weekday(
    client: TestClient, db_session
) -> None:
    token = register_citizen(client)
    auth = {"Authorization": f"Bearer {token}"}

    city_clinic = _make_facility(db_session, name="HealthLink City Clinic")
    river_hospital = _make_facility(db_session, name="HealthLink River Hospital")

    _make_doctor(
        db_session,
        first_name="Amina",
        last_name="Rahman",
        facility=city_clinic,
    )
    target_user_id, _ = _make_doctor(
        db_session,
        first_name="Sabbir",
        last_name="Hossain",
        facility=river_hospital,
    )
    _make_doctor(
        db_session,
        first_name="Lima",
        last_name="Akter",
        facility=river_hospital,
    )

    # Add a Sunday practice schedule for the target doctor
    from app.doctors.models import DoctorPracticeSchedule, PracticeScheduleStatus
    from app.doctors.models import PracticeWeekday

    schedule = DoctorPracticeSchedule(
        doctor_user_id=target_user_id,
        facility_id=river_hospital.id,
        weekday=PracticeWeekday.SUNDAY.value,
        start_time=__import__("datetime").time(16, 0),
        end_time=__import__("datetime").time(21, 0),
        max_patients=30,
        status=PracticeScheduleStatus.ACTIVE.value,
    )
    db_session.add(schedule)
    db_session.commit()

    # Name filter
    response = client.get(
        CITIZEN_SEARCH_PATH,
        params={"name": "Sabbir"},
        headers=auth,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(target_user_id)
    assert payload[0]["facility_name"] == "HealthLink River Hospital"
    assert payload[0]["specialization"] == "Doctor"
    # NID MUST NOT be exposed
    assert "nid_number" not in payload[0]
    assert "bmdc_registration_number" not in payload[0]

    # Facility filter
    response = client.get(
        CITIZEN_SEARCH_PATH,
        params={"facility_name": "river"},
        headers=auth,
    )
    assert response.status_code == 200
    payload = response.json()
    assert {row["id"] for row in payload} == {str(target_user_id)} | {
        str(row["id"]) for row in payload if row["id"] != str(target_user_id)
    }
    assert len(payload) == 2

    # Weekday filter
    response = client.get(
        CITIZEN_SEARCH_PATH,
        params={"weekday": "SUNDAY"},
        headers=auth,
    )
    assert response.status_code == 200
    payload = response.json()
    assert [row["id"] for row in payload] == [str(target_user_id)]


def test_doctor_search_hides_unverified_doctors(
    client: TestClient, db_session
) -> None:
    token = register_citizen(client)
    auth = {"Authorization": f"Bearer {token}"}

    facility = _make_facility(db_session, name="HealthLink Pending Clinic")
    _make_doctor(
        db_session,
        first_name="Pending",
        last_name="Doctor",
        facility=facility,
        verified=False,
    )

    response = client.get(
        CITIZEN_SEARCH_PATH,
        params={"facility_name": "Pending"},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json() == []


def test_citizen_doctor_profile_includes_practice_days(
    client: TestClient, db_session
) -> None:
    token = register_citizen(client)
    auth = {"Authorization": f"Bearer {token}"}

    facility = _make_facility(db_session, name="HealthLink Profile Clinic")
    doctor_user_id, _ = _make_doctor(
        db_session,
        first_name="Profile",
        last_name="Doctor",
        facility=facility,
    )

    from datetime import time
    from app.doctors.models import (
        DoctorPracticeSchedule,
        PracticeScheduleStatus,
        PracticeWeekday,
    )

    rows = [
        DoctorPracticeSchedule(
            doctor_user_id=doctor_user_id,
            facility_id=facility.id,
            weekday=PracticeWeekday.SUNDAY.value,
            start_time=time(16, 0),
            end_time=time(21, 0),
            max_patients=30,
            status=PracticeScheduleStatus.ACTIVE.value,
        ),
        DoctorPracticeSchedule(
            doctor_user_id=doctor_user_id,
            facility_id=facility.id,
            weekday=PracticeWeekday.TUESDAY.value,
            start_time=time(16, 0),
            end_time=time(21, 0),
            max_patients=30,
            status=PracticeScheduleStatus.ACTIVE.value,
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()

    response = client.get(
        CITIZEN_PROFILE_PATH.format(doctor_user_id=doctor_user_id),
        headers=auth,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["first_name"] == "Profile"
    assert body["facility_name"] == "HealthLink Profile Clinic"
    assert {row["weekday"] for row in body["practice_days"]} == {"SUNDAY", "TUESDAY"}
    assert "nid_number" not in body
    assert "bmdc_number" not in body

    response = client.get(
        PRACTICE_DAYS_PATH.format(doctor_user_id=doctor_user_id),
        headers=auth,
    )
    assert response.status_code == 200
    body = response.json()
    assert {row["facility_id"] for row in body} == {str(facility.id)}


def test_citizen_doctor_profile_returns_404_for_unknown_or_unverified_doctor(
    client: TestClient, db_session
) -> None:
    token = register_citizen(client)
    auth = {"Authorization": f"Bearer {token}"}

    unknown = uuid.uuid4()
    response = client.get(
        CITIZEN_PROFILE_PATH.format(doctor_user_id=unknown),
        headers=auth,
    )
    assert response.status_code == 404

    # Created-but-pending doctor should not be surfaceable
    facility = _make_facility(db_session, name="Hidden Clinic")
    pending_doctor_id, _ = _make_doctor(
        db_session,
        first_name="Pending",
        last_name="Pending",
        facility=facility,
        verified=False,
    )
    response = client.get(
        CITIZEN_PROFILE_PATH.format(doctor_user_id=pending_doctor_id),
        headers=auth,
    )
    assert response.status_code == 404


def test_admin_can_also_search_doctors(client: TestClient, db_session) -> None:
    auth = _admin_headers(client, db_session)
    facility = _make_facility(db_session, name="Admin Discovery Clinic")
    _make_doctor(
        db_session,
        first_name="Admin",
        last_name="Searchable",
        facility=facility,
    )
    response = client.get(
        CITIZEN_SEARCH_PATH,
        params={"facility_name": "Admin"},
        headers=auth,
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
