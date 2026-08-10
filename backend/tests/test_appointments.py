from __future__ import annotations

import uuid
from datetime import date, time

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.models import User
from app.citizens.models import CitizenProfile
from app.doctors.models import DoctorPracticeSchedule, PracticeScheduleStatus
from app.facilities.models import HealthcareFacility
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.models import (
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)


CITIZEN_PASSWORD = "StrongPassword123!"
BOOK_PATH = "/api/v1/citizens/appointments"
HISTORY_PATH = "/api/v1/citizens/appointments"


def _register_citizen(client: TestClient) -> tuple[str, uuid.UUID]:
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
    return login.json()["access_token"], response.json()["citizen_id"]


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
) -> uuid.UUID:
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
    return user.id


def _add_schedule(
    db_session,
    *,
    doctor_user_id: uuid.UUID,
    facility: HealthcareFacility,
    weekday: str,
    max_patients: int = 5,
) -> DoctorPracticeSchedule:
    schedule = DoctorPracticeSchedule(
        doctor_user_id=doctor_user_id,
        facility_id=facility.id,
        weekday=weekday,
        start_time=time(9, 0),
        end_time=time(13, 0),
        max_patients=max_patients,
        status=PracticeScheduleStatus.ACTIVE.value,
    )
    db_session.add(schedule)
    db_session.commit()
    db_session.refresh(schedule)
    return schedule


def test_booking_requires_authentication(client: TestClient) -> None:
    response = client.post(
        BOOK_PATH,
        json={
            "doctor_user_id": str(uuid.uuid4()),
            "facility_id": str(uuid.uuid4()),
            "appointment_date": "2099-01-05",
            "reason": "Checkup",
        },
    )
    assert response.status_code == 401


def test_booking_rejects_unverified_doctor(
    client: TestClient, db_session
) -> None:
    token, _ = _register_citizen(client)
    facility = _make_facility(db_session, name="Booking Unverified Clinic")
    doctor_user_id = _make_doctor(
        db_session,
        first_name="Pending",
        last_name="Doctor",
        facility=facility,
        verified=False,
    )
    response = client.post(
        BOOK_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "doctor_user_id": str(doctor_user_id),
            "facility_id": str(facility.id),
            "appointment_date": "2099-01-05",
        },
    )
    assert response.status_code == 404


def test_booking_rejects_when_no_active_schedule(
    client: TestClient, db_session
) -> None:
    token, _ = _register_citizen(client)
    facility = _make_facility(db_session, name="Booking Closed Clinic")
    doctor_user_id = _make_doctor(
        db_session,
        first_name="Closed",
        last_name="Doctor",
        facility=facility,
    )
    # Date selected maps to a weekday the doctor has no schedule for.
    response = client.post(
        BOOK_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "doctor_user_id": str(doctor_user_id),
            "facility_id": str(facility.id),
            "appointment_date": "2099-01-05",  # Monday
        },
    )
    assert response.status_code == 409
    body = response.json()
    assert "schedule" in body["detail"].lower()


def test_booking_assigns_serial_one_then_increments(
    client: TestClient, db_session
) -> None:
    token, _ = _register_citizen(client)
    auth = {"Authorization": f"Bearer {token}"}
    facility = _make_facility(db_session, name="Booking Serial Clinic")
    doctor_user_id = _make_doctor(
        db_session,
        first_name="Serial",
        last_name="Doctor",
        facility=facility,
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=5,
    )

    first = client.post(
        BOOK_PATH,
        headers=auth,
        json={
            "doctor_user_id": str(doctor_user_id),
            "facility_id": str(facility.id),
            "appointment_date": "2099-01-05",
            "reason": "First",
        },
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["serial_number"] == 1
    assert body["status"] == "BOOKED"
    assert body["facility_name"] == "Booking Serial Clinic"
    assert body["queue"]["queue_status"] == "WAITING"

    second = client.post(
        BOOK_PATH,
        headers=auth,
        json={
            "doctor_user_id": str(doctor_user_id),
            "facility_id": str(facility.id),
            "appointment_date": "2099-01-05",
            "reason": "Second",
        },
    )
    assert second.status_code == 201, second.text
    assert second.json()["serial_number"] == 2


def test_booking_max_serial_jumps_after_cancellation(
    client: TestClient, db_session
) -> None:
    """Cancelled serials are never reused (V6 section 16 example)."""
    from datetime import datetime, timezone

    from app.appointments.models import (
        Appointment,
        AppointmentStatus,
    )

    token, _ = _register_citizen(client)
    auth = {"Authorization": f"Bearer {token}"}
    facility = _make_facility(db_session, name="Booking Cancel Clinic")
    doctor_user_id = _make_doctor(
        db_session,
        first_name="Cancel",
        last_name="Doctor",
        facility=facility,
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=10,
    )

    serials = []
    for _ in range(3):
        response = client.post(
            BOOK_PATH,
            headers=auth,
            json={
                "doctor_user_id": str(doctor_user_id),
                "facility_id": str(facility.id),
                "appointment_date": "2099-01-05",
            },
        )
        assert response.status_code == 201
        serials.append(response.json()["serial_number"])
    assert serials == [1, 2, 3]

    # Cancel the middle serial directly via the model so the next booking
    # must pick MAX(serial)+1, not the freed slot.
    middle = db_session.execute(
        select(Appointment).where(Appointment.serial_number == 2)
    ).scalar_one()
    middle.status = AppointmentStatus.CANCELLED.value
    middle.cancelled_at = datetime.now(timezone.utc)
    db_session.commit()

    response = client.post(
        BOOK_PATH,
        headers=auth,
        json={
            "doctor_user_id": str(doctor_user_id),
            "facility_id": str(facility.id),
            "appointment_date": "2099-01-05",
        },
    )
    assert response.status_code == 201
    assert response.json()["serial_number"] == 4


def test_booking_enforces_daily_capacity(
    client: TestClient, db_session
) -> None:
    """Capacity is enforced against active appointments, not MAX(serial)."""
    from datetime import datetime, timezone

    from app.appointments.models import Appointment, AppointmentStatus

    token, _ = _register_citizen(client)
    auth = {"Authorization": f"Bearer {token}"}
    facility = _make_facility(db_session, name="Booking Capacity Clinic")
    doctor_user_id = _make_doctor(
        db_session,
        first_name="Capacity",
        last_name="Doctor",
        facility=facility,
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=2,
    )

    # Seed capacity manually: two active appointments and one cancelled.
    registration = db_session.scalar(
        select(ProfessionalRoleRegistration).where(
            ProfessionalRoleRegistration.facility_id == facility.id,
        )
    )
    citizen_profile = db_session.scalar(select(CitizenProfile))
    assert citizen_profile is not None

    for serial, status in (
        (1, AppointmentStatus.BOOKED.value),
        (2, AppointmentStatus.BOOKED.value),
        (3, AppointmentStatus.CANCELLED.value),
    ):
        appointment = Appointment(
            citizen_id=citizen_profile.id,
            doctor_role_registration_id=registration.id,
            facility_id=facility.id,
            appointment_date=date(2099, 1, 5),
            serial_number=serial,
            status=status,
            booked_at=datetime.now(timezone.utc),
        )
        if status == AppointmentStatus.CANCELLED.value:
            appointment.cancelled_at = datetime.now(timezone.utc)
        db_session.add(appointment)
    db_session.commit()

    response = client.post(
        BOOK_PATH,
        headers=auth,
        json={
            "doctor_user_id": str(doctor_user_id),
            "facility_id": str(facility.id),
            "appointment_date": "2099-01-05",
        },
    )
    assert response.status_code == 409
    assert "capacity" in response.json()["detail"].lower()


def test_booking_rejects_past_date(client: TestClient, db_session) -> None:
    token, _ = _register_citizen(client)
    facility = _make_facility(db_session, name="Booking Past Clinic")
    doctor_user_id = _make_doctor(
        db_session,
        first_name="Past",
        last_name="Doctor",
        facility=facility,
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=5,
    )
    response = client.post(
        BOOK_PATH,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "doctor_user_id": str(doctor_user_id),
            "facility_id": str(facility.id),
            "appointment_date": "2000-01-03",
        },
    )
    assert response.status_code == 422


def test_history_lists_citizen_appointments(
    client: TestClient, db_session
) -> None:
    token, _ = _register_citizen(client)
    auth = {"Authorization": f"Bearer {token}"}
    facility = _make_facility(db_session, name="Booking History Clinic")
    doctor_user_id = _make_doctor(
        db_session,
        first_name="History",
        last_name="Doctor",
        facility=facility,
    )
    _add_schedule(
        db_session,
        doctor_user_id=doctor_user_id,
        facility=facility,
        weekday="MONDAY",
        max_patients=5,
    )

    for _ in range(2):
        client.post(
            BOOK_PATH,
            headers=auth,
            json={
                "doctor_user_id": str(doctor_user_id),
                "facility_id": str(facility.id),
                "appointment_date": "2099-01-05",
            },
        )

    response = client.get(HISTORY_PATH, headers=auth)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["appointments"]) == 2
    serials = [row["serial_number"] for row in body["appointments"]]
    assert serials == [1, 2]
    assert body["appointments"][0]["doctor_name"] == "History Doctor"
    assert body["appointments"][0]["facility_name"] == "Booking History Clinic"
    assert body["appointments"][0]["status"] == "BOOKED"


def test_history_requires_authentication(client: TestClient) -> None:
    response = client.get(HISTORY_PATH)
    assert response.status_code == 401
