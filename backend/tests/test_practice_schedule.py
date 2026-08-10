from __future__ import annotations

import uuid
from datetime import time

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.admins.provisioning import create_trusted_admin
from app.auth.models import User
from app.doctors.models import (
    DoctorPracticeSchedule,
    PracticeScheduleStatus,
    PracticeWeekday,
)
from app.facilities.models import HealthcareFacility
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.models import (
    DoctorRegistrationDetail,
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)


ADMIN_PASSWORD = "StrongAdminPassword123!"
PROFESSIONAL_PASSWORD = "StrongPassword123!"


def _admin_headers(client: TestClient, db_session) -> tuple[dict[str, str], User]:
    provisioned = create_trusted_admin(
        db_session,
        email=f"admin-{uuid.uuid4().hex}@example.com",
        password=ADMIN_PASSWORD,
        first_name="Admin",
        last_name="User",
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
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, provisioned.user


def _make_facility(db_session, *, name: str = "Schedule Clinic") -> HealthcareFacility:
    facility = HealthcareFacility(
        name=name,
        facility_type="CLINIC",
        registration_number=f"REG-{uuid.uuid4().hex[:8]}",
        address="Schedule Avenue",
        phone="+8801700000000",
        email="schedule@example.com",
        is_active=True,
    )
    db_session.add(facility)
    db_session.commit()
    db_session.refresh(facility)
    return facility


def _make_verified_doctor(
    db_session,
    *,
    facility: HealthcareFacility | None = None,
    role_code: str = ProfessionalRoleCode.DOCTOR.value,
) -> tuple[uuid.UUID, ProfessionalRoleRegistration, User]:
    """Create a verified professional with an active session.

    Returns ``(user_id, registration, user)`` for the freshly created user.
    """
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"doctor-{unique}@example.com",
        password_hash="phase-1-test-password-hash",
        first_name="Verified",
        last_name="Doctor",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = HealthcareProfessionalProfile(user_id=user.id)
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    role = db_session.scalar(
        select(ProfessionalRole).where(ProfessionalRole.code == role_code)
    )
    assert role is not None

    from datetime import datetime, timezone

    registration = ProfessionalRoleRegistration(
        professional_id=profile.id,
        role_id=role.id,
        facility_id=facility.id if facility else None,
        facility_name_submitted=facility.name if facility else "Submitted Clinic",
        designation="Consultant",
        verification_status=VerificationStatus.VERIFIED.value,
        verified_at=datetime.now(timezone.utc),
    )
    db_session.add(registration)
    db_session.commit()
    db_session.refresh(registration)

    if role_code == ProfessionalRoleCode.DOCTOR.value:
        detail = DoctorRegistrationDetail(
            professional_role_registration_id=registration.id,
            bmdc_registration_number=f"BMDC-{unique}",
        )
        db_session.add(detail)
        db_session.commit()

    return user.id, registration, user


def _register_professional_through_endpoint(client: TestClient, *, role_code: str) -> tuple[str, str]:
    unique = uuid.uuid4().hex[:10]
    payload = {
        "email": f"doctor-{unique}@example.com",
        "password": PROFESSIONAL_PASSWORD,
        "first_name": "Pending",
        "last_name": "Doctor",
        "nid_number": f"NID-{unique}",
        "role_code": role_code,
        "facility_name": "Submitted Facility",
        "designation": "Consultant",
        "additional_info": "test",
    }
    if role_code == ProfessionalRoleCode.DOCTOR.value:
        payload["bmdc_registration_number"] = f"BMDC-{unique}"
    response = client.post(
        "/api/v1/auth/professional/register",
        json=payload,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["user_id"], payload["email"]


def _admin_verify(
    client: TestClient,
    admin_headers: dict[str, str],
    *,
    user_id: str,
    role_registration_id: str,
    facility_id: str,
) -> None:
    response = client.post(
        f"/api/v1/admin/professional-registrations/{role_registration_id}/verify",
        headers=admin_headers,
        json={"facility_id": facility_id},
    )
    assert response.status_code == 200, response.text
    _ = user_id  # silence unused-arg warnings; the helper is the contract


def _login_as_professional(
    client: TestClient,
    *,
    email: str,
    nid_number: str,
    role_code: str,
) -> str:
    response = client.post(
        "/api/v1/auth/professional/login",
        json={
            "nid_number": nid_number,
            "password": PROFESSIONAL_PASSWORD,
            "role_code": role_code,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# Doctor self-management endpoints
# ---------------------------------------------------------------------------


def test_unauthenticated_cannot_manage_practice_schedule(
    client: TestClient,
) -> None:
    for path, method in [
        ("/api/v1/professionals/me/practice-schedule", "GET"),
        ("/api/v1/professionals/me/practice-schedule", "POST"),
        (
            f"/api/v1/professionals/me/practice-schedule/{uuid.uuid4()}",
            "PUT",
        ),
        (
            f"/api/v1/professionals/me/practice-schedule/{uuid.uuid4()}",
            "DELETE",
        ),
    ]:
        response = client.request(method, path)
        assert response.status_code == 401, (method, path, response.status_code)


def test_non_doctor_professionals_cannot_manage_practice_schedule(
    client: TestClient, db_session
) -> None:
    # Register a NURSE professional, admin-verifies against a facility
    admin_auth, _ = _admin_headers(client, db_session)
    facility = _make_facility(db_session, name="Nurse Practice Clinic")
    nurse_user_id, nurse_email = _register_professional_through_endpoint(
        client, role_code=ProfessionalRoleCode.NURSE.value
    )
    # Get the role registration id
    from app.professionals.models import ProfessionalRoleRegistration as PRR
    from app.professionals.models import HealthcareProfessionalProfile as HCP

    nurse = db_session.scalar(select(User).where(User.id == uuid.UUID(nurse_user_id)))
    profile = db_session.scalar(
        select(HCP).where(HCP.user_id == nurse.id)
    )
    registration = db_session.scalar(
        select(PRR).where(PRR.professional_id == profile.id)
    )
    _admin_verify(
        client,
        admin_auth,
        user_id=nurse_user_id,
        role_registration_id=str(registration.id),
        facility_id=str(facility.id),
    )

    # Manually set NID on the user so the nurse can log in via the
    # NID-based professional login flow.
    from app.citizens.models import UserNationalIdentifier

    nid_number = next(
        nid
        for nid in db_session.scalars(
            select(UserNationalIdentifier).where(
                UserNationalIdentifier.user_id == nurse.id
            )
        )
        if nid is not None
    ).nid_number
    # The registration above creates a UserNationalIdentifier via register_new.
    token = _login_as_professional(
        client,
        email=nurse_email,
        nid_number=nid_number,
        role_code=ProfessionalRoleCode.NURSE.value,
    )
    response = client.get(
        "/api/v1/professionals/me/practice-schedule",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_doctor_can_create_list_update_and_delete_practice_schedule(
    client: TestClient, db_session
) -> None:
    admin_auth, _ = _admin_headers(client, db_session)
    facility = _make_facility(db_session, name="Verified Schedule Clinic")
    doctor_user_id, doctor_email = _register_professional_through_endpoint(
        client, role_code=ProfessionalRoleCode.DOCTOR.value
    )
    from app.professionals.models import ProfessionalRoleRegistration as PRR
    from app.professionals.models import HealthcareProfessionalProfile as HCP
    from app.citizens.models import UserNationalIdentifier

    user = db_session.scalar(select(User).where(User.id == uuid.UUID(doctor_user_id)))
    profile = db_session.scalar(select(HCP).where(HCP.user_id == user.id))
    registration = db_session.scalar(
        select(PRR).where(PRR.professional_id == profile.id)
    )
    _admin_verify(
        client,
        admin_auth,
        user_id=doctor_user_id,
        role_registration_id=str(registration.id),
        facility_id=str(facility.id),
    )
    nid = db_session.scalar(
        select(UserNationalIdentifier).where(UserNationalIdentifier.user_id == user.id)
    ).nid_number
    token = _login_as_professional(
        client,
        email=doctor_email,
        nid_number=nid,
        role_code=ProfessionalRoleCode.DOCTOR.value,
    )
    auth = {"Authorization": f"Bearer {token}"}

    # Create
    create_response = client.post(
        "/api/v1/professionals/me/practice-schedule",
        headers=auth,
        json={
            "facility_id": str(facility.id),
            "weekday": "SUNDAY",
            "start_time": "16:00",
            "end_time": "21:00",
            "max_patients": 30,
            "status": "ACTIVE",
        },
    )
    assert create_response.status_code == 201, create_response.text
    schedule_id = create_response.json()["schedule"]["id"]

    # List
    list_response = client.get(
        "/api/v1/professionals/me/practice-schedule",
        headers=auth,
    )
    assert list_response.status_code == 200
    body = list_response.json()
    assert len(body) == 1
    assert body[0]["id"] == schedule_id

    # Update
    update_response = client.put(
        f"/api/v1/professionals/me/practice-schedule/{schedule_id}",
        headers=auth,
        json={
            "facility_id": str(facility.id),
            "weekday": "TUESDAY",
            "start_time": "15:00",
            "end_time": "20:00",
            "max_patients": 25,
            "status": "ACTIVE",
        },
    )
    assert update_response.status_code == 200, update_response.text
    body = update_response.json()
    assert body["weekday"] == "TUESDAY"
    assert body["max_patients"] == 25

    # Conflict: try to add an overlapping Sunday schedule
    overlap_response = client.post(
        "/api/v1/professionals/me/practice-schedule",
        headers=auth,
        json={
            "facility_id": str(facility.id),
            "weekday": "TUESDAY",
            "start_time": "19:00",
            "end_time": "22:00",
            "max_patients": 10,
            "status": "ACTIVE",
        },
    )
    assert overlap_response.status_code == 409

    # Validation: end <= start
    invalid_response = client.post(
        "/api/v1/professionals/me/practice-schedule",
        headers=auth,
        json={
            "facility_id": str(facility.id),
            "weekday": "WEDNESDAY",
            "start_time": "20:00",
            "end_time": "16:00",
            "max_patients": 10,
            "status": "ACTIVE",
        },
    )
    assert invalid_response.status_code == 422

    # Delete
    delete_response = client.delete(
        f"/api/v1/professionals/me/practice-schedule/{schedule_id}",
        headers=auth,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == schedule_id

    # Listing again should yield empty
    list_after = client.get(
        "/api/v1/professionals/me/practice-schedule",
        headers=auth,
    )
    assert list_after.status_code == 200
    assert list_after.json() == []


def test_doctor_cannot_manage_other_doctors_schedule(
    client: TestClient, db_session
) -> None:
    admin_auth, _ = _admin_headers(client, db_session)
    facility = _make_facility(db_session, name="Isolation Clinic")

    # Doctor A
    doctor_a_id, doctor_a_email = _register_professional_through_endpoint(
        client, role_code=ProfessionalRoleCode.DOCTOR.value
    )
    from app.professionals.models import ProfessionalRoleRegistration as PRR
    from app.professionals.models import HealthcareProfessionalProfile as HCP
    from app.citizens.models import UserNationalIdentifier

    user_a = db_session.scalar(select(User).where(User.id == uuid.UUID(doctor_a_id)))
    profile_a = db_session.scalar(select(HCP).where(HCP.user_id == user_a.id))
    registration_a = db_session.scalar(
        select(PRR).where(PRR.professional_id == profile_a.id)
    )
    _admin_verify(
        client,
        admin_auth,
        user_id=doctor_a_id,
        role_registration_id=str(registration_a.id),
        facility_id=str(facility.id),
    )
    nid_a = db_session.scalar(
        select(UserNationalIdentifier).where(UserNationalIdentifier.user_id == user_a.id)
    ).nid_number
    token_a = _login_as_professional(
        client,
        email=doctor_a_email,
        nid_number=nid_a,
        role_code=ProfessionalRoleCode.DOCTOR.value,
    )

    # Doctor A creates a schedule row directly in DB to simulate ownership
    schedule = DoctorPracticeSchedule(
        doctor_user_id=user_a.id,
        facility_id=facility.id,
        weekday=PracticeWeekday.SUNDAY.value,
        start_time=time(16, 0),
        end_time=time(21, 0),
        max_patients=30,
        status=PracticeScheduleStatus.ACTIVE.value,
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)

    # Doctor B
    doctor_b_id, doctor_b_email = _register_professional_through_endpoint(
        client, role_code=ProfessionalRoleCode.DOCTOR.value
    )
    user_b = db_session.scalar(select(User).where(User.id == uuid.UUID(doctor_b_id)))
    profile_b = db_session.scalar(select(HCP).where(HCP.user_id == user_b.id))
    registration_b = db_session.scalar(
        select(PRR).where(PRR.professional_id == profile_b.id)
    )
    _admin_verify(
        client,
        admin_auth,
        user_id=doctor_b_id,
        role_registration_id=str(registration_b.id),
        facility_id=str(facility.id),
    )
    nid_b = db_session.scalar(
        select(UserNationalIdentifier).where(UserNationalIdentifier.user_id == user_b.id)
    ).nid_number
    token_b = _login_as_professional(
        client,
        email=doctor_b_email,
        nid_number=nid_b,
        role_code=ProfessionalRoleCode.DOCTOR.value,
    )

    # Doctor B tries to update Doctor A's schedule
    response = client.put(
        f"/api/v1/professionals/me/practice-schedule/{schedule.id}",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "facility_id": str(facility.id),
            "weekday": "SUNDAY",
            "start_time": "17:00",
            "end_time": "22:00",
            "max_patients": 30,
            "status": "ACTIVE",
        },
    )
    assert response.status_code == 404


def test_inactive_facility_rejected_on_schedule_creation(
    client: TestClient, db_session
) -> None:
    admin_auth, _ = _admin_headers(client, db_session)
    facility = _make_facility(db_session, name="Disabled Facility")
    facility.is_active = False
    db_session.commit()

    doctor_user_id, doctor_email = _register_professional_through_endpoint(
        client, role_code=ProfessionalRoleCode.DOCTOR.value
    )
    from app.professionals.models import ProfessionalRoleRegistration as PRR
    from app.professionals.models import HealthcareProfessionalProfile as HCP
    from app.citizens.models import UserNationalIdentifier

    user = db_session.scalar(select(User).where(User.id == uuid.UUID(doctor_user_id)))
    profile = db_session.scalar(select(HCP).where(HCP.user_id == user.id))
    registration = db_session.scalar(
        select(PRR).where(PRR.professional_id == profile.id)
    )
    # First verify with the facility still active to bind a registration
    facility.is_active = True
    db_session.commit()
    _admin_verify(
        client,
        admin_auth,
        user_id=doctor_user_id,
        role_registration_id=str(registration.id),
        facility_id=str(facility.id),
    )
    facility.is_active = False
    db_session.commit()
    nid = db_session.scalar(
        select(UserNationalIdentifier).where(UserNationalIdentifier.user_id == user.id)
    ).nid_number
    token = _login_as_professional(
        client,
        email=doctor_email,
        nid_number=nid,
        role_code=ProfessionalRoleCode.DOCTOR.value,
    )

    response = client.post(
        "/api/v1/professionals/me/practice-schedule",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "facility_id": str(facility.id),
            "weekday": "MONDAY",
            "start_time": "10:00",
            "end_time": "12:00",
            "max_patients": 5,
            "status": "ACTIVE",
        },
    )
    assert response.status_code == 400