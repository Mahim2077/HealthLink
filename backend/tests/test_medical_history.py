from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.appointments.models import (
    Appointment,
    AppointmentQueueEntry,
    AppointmentStatus,
    DoctorPracticeSession,
    QueueStatus,
    SessionStatus,
)
from app.auth.constants import Portal
from app.auth.models import User
from app.auth.service import AuthService
from app.citizens.models import CitizenProfile
from app.core.config import Settings
from app.facilities.models import HealthcareFacility
from app.prescriptions.models import Prescription, PrescriptionItem
from app.professionals.constants import ProfessionalRoleCode, VerificationStatus
from app.professionals.models import (
    HealthcareProfessionalProfile,
    ProfessionalRole,
    ProfessionalRoleRegistration,
)
from app.visits.models import MedicalVisit, VisitStatus


CITIZEN_PATH = "/api/v1/citizens/me/medical-history"
PROFESSIONAL_PATH = "/api/v1/professionals/current-patient/medical-history"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _user(db_session, name: str) -> User:
    user = User(
        email=f"{name.lower()}-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="test-password-hash",
        first_name=name,
        last_name="Tester",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _citizen(db_session, name: str) -> CitizenProfile:
    user = _user(db_session, name)
    profile = CitizenProfile(
        user_id=user.id,
        date_of_birth=date(1990, 1, 1),
        gender="OTHER",
        blood_group="O+",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def _facility(db_session) -> HealthcareFacility:
    facility = HealthcareFacility(
        name="History Medical Centre",
        facility_type="HOSPITAL",
        address="Dhaka",
        is_active=True,
    )
    db_session.add(facility)
    db_session.commit()
    db_session.refresh(facility)
    return facility


def _professional(
    db_session,
    facility: HealthcareFacility,
    *,
    role_code: ProfessionalRoleCode = ProfessionalRoleCode.DOCTOR,
) -> tuple[User, ProfessionalRoleRegistration]:
    user = _user(db_session, role_code.value)
    profile = HealthcareProfessionalProfile(user_id=user.id)
    db_session.add(profile)
    db_session.flush()
    role = db_session.scalar(
        select(ProfessionalRole).where(ProfessionalRole.code == role_code.value)
    )
    assert role is not None
    registration = ProfessionalRoleRegistration(
        professional_id=profile.id,
        role_id=role.id,
        facility_id=facility.id,
        facility_name_submitted=facility.name,
        designation="Consultant",
        verification_status=VerificationStatus.VERIFIED.value,
        verified_at=datetime(2026, 7, 1, tzinfo=UTC),
    )
    db_session.add(registration)
    db_session.commit()
    db_session.refresh(registration)
    return user, registration


def _token(
    db_session,
    settings: Settings,
    user: User,
    portal: Portal,
    *,
    role_registration_id: uuid.UUID | None = None,
) -> str:
    return AuthService(db_session, settings).create_session(
        user.id,
        portal,
        active_professional_role_registration_id=role_registration_id,
    ).access_token


def _visit(
    db_session,
    *,
    citizen: CitizenProfile,
    registration: ProfessionalRoleRegistration,
    facility: HealthcareFacility,
    finalized_at: datetime | None,
    diagnosis: str,
) -> MedicalVisit:
    visit = MedicalVisit(
        citizen_id=citizen.id,
        doctor_role_registration_id=registration.id,
        facility_id=facility.id,
        visit_date=finalized_at or datetime(2026, 8, 3, 10, tzinfo=UTC),
        chief_complaint=f"Complaint for {diagnosis}",
        diagnosis=diagnosis,
        status=(
            VisitStatus.FINALIZED.value
            if finalized_at is not None
            else VisitStatus.DRAFT.value
        ),
        finalized_at=finalized_at,
    )
    db_session.add(visit)
    db_session.commit()
    db_session.refresh(visit)
    return visit


def _prescription(
    db_session,
    *,
    visit: MedicalVisit,
    registration: ProfessionalRoleRegistration,
    created_at: datetime,
) -> Prescription:
    prescription = Prescription(
        visit_id=visit.id,
        citizen_id=visit.citizen_id,
        author_doctor_role_registration_id=registration.id,
        diagnostic_information="Recorded diagnostic context",
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(prescription)
    db_session.flush()
    db_session.add(
        PrescriptionItem(
            prescription_id=prescription.id,
            medicine_name="Medicine A",
            dosage="1 tablet",
            frequency="Daily",
            duration="5 days",
        )
    )
    db_session.commit()
    db_session.refresh(prescription)
    return prescription


def _make_current(
    db_session,
    *,
    citizen: CitizenProfile,
    doctor_registration: ProfessionalRoleRegistration,
    facility: HealthcareFacility,
) -> None:
    practice_session = DoctorPracticeSession(
        doctor_role_registration_id=doctor_registration.id,
        facility_id=facility.id,
        session_date=date(2026, 8, 10),
        status=SessionStatus.ACTIVE.value,
        started_at=datetime(2026, 8, 10, 8, tzinfo=UTC),
    )
    appointment = Appointment(
        citizen_id=citizen.id,
        doctor_role_registration_id=doctor_registration.id,
        facility_id=facility.id,
        appointment_date=date(2026, 8, 10),
        serial_number=1,
        status=AppointmentStatus.BOOKED.value,
        booked_at=datetime(2026, 8, 1, 8, tzinfo=UTC),
    )
    db_session.add_all([practice_session, appointment])
    db_session.flush()
    db_session.add(
        AppointmentQueueEntry(
            appointment_id=appointment.id,
            practice_session_id=practice_session.id,
            queue_status=QueueStatus.CURRENT.value,
            became_current_at=datetime(2026, 8, 10, 8, 5, tzinfo=UTC),
        )
    )
    db_session.commit()


def test_history_routes_require_authentication(client: TestClient) -> None:
    assert client.get(CITIZEN_PATH).status_code == 401
    assert client.get(PROFESSIONAL_PATH).status_code == 401


def test_citizen_history_is_owned_derived_and_hides_drafts(
    client: TestClient,
    db_session,
    test_settings: Settings,
) -> None:
    facility = _facility(db_session)
    doctor, registration = _professional(db_session, facility)
    citizen = _citizen(db_session, "Citizen")
    other = _citizen(db_session, "Other")
    first = _visit(
        db_session,
        citizen=citizen,
        registration=registration,
        facility=facility,
        finalized_at=datetime(2026, 8, 1, 10, tzinfo=UTC),
        diagnosis="First diagnosis",
    )
    prescription = _prescription(
        db_session,
        visit=first,
        registration=registration,
        created_at=datetime(2026, 8, 1, 11, tzinfo=UTC),
    )
    second = _visit(
        db_session,
        citizen=citizen,
        registration=registration,
        facility=facility,
        finalized_at=datetime(2026, 8, 2, 10, tzinfo=UTC),
        diagnosis="Second diagnosis",
    )
    _visit(
        db_session,
        citizen=citizen,
        registration=registration,
        facility=facility,
        finalized_at=None,
        diagnosis="Private draft",
    )
    _visit(
        db_session,
        citizen=other,
        registration=registration,
        facility=facility,
        finalized_at=datetime(2026, 8, 4, 10, tzinfo=UTC),
        diagnosis="Other citizen diagnosis",
    )

    token = _token(
        db_session, test_settings, citizen.user, Portal.CITIZEN
    )
    response = client.get(CITIZEN_PATH, headers=_auth(token))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 3
    assert [row["resource_id"] for row in payload["items"]] == [
        str(second.id),
        str(prescription.id),
        str(first.id),
    ]
    assert {row["resource_type"] for row in payload["items"]} == {
        "VISIT",
        "PRESCRIPTION",
    }
    assert all(row["facility"] == facility.name for row in payload["items"])
    assert all(row["professional"].startswith("Dr ") for row in payload["items"])
    assert "Private draft" not in response.text
    assert "Other citizen diagnosis" not in response.text
    assert doctor.email not in response.text


def test_history_filters_and_pagination_are_stable(
    client: TestClient,
    db_session,
    test_settings: Settings,
) -> None:
    facility = _facility(db_session)
    _, registration = _professional(db_session, facility)
    citizen = _citizen(db_session, "Filtered")
    first = _visit(
        db_session,
        citizen=citizen,
        registration=registration,
        facility=facility,
        finalized_at=datetime(2026, 8, 1, 10, tzinfo=UTC),
        diagnosis="Older",
    )
    _prescription(
        db_session,
        visit=first,
        registration=registration,
        created_at=datetime(2026, 8, 1, 11, tzinfo=UTC),
    )
    newest = _visit(
        db_session,
        citizen=citizen,
        registration=registration,
        facility=facility,
        finalized_at=datetime(2026, 8, 2, 10, tzinfo=UTC),
        diagnosis="Newest",
    )
    token = _token(db_session, test_settings, citizen.user, Portal.CITIZEN)

    page_one = client.get(
        f"{CITIZEN_PATH}?page=1&page_size=1", headers=_auth(token)
    ).json()
    page_two = client.get(
        f"{CITIZEN_PATH}?page=2&page_size=1", headers=_auth(token)
    ).json()
    assert page_one["items"][0]["resource_id"] == str(newest.id)
    assert page_one["has_next"] is True
    assert page_two["items"][0]["resource_type"] == "PRESCRIPTION"

    visits = client.get(
        f"{CITIZEN_PATH}?resource_type=VISIT", headers=_auth(token)
    ).json()
    assert visits["total"] == 2
    assert all(row["resource_type"] == "VISIT" for row in visits["items"])

    one_day = client.get(
        f"{CITIZEN_PATH}?date_from=2026-08-02&date_to=2026-08-02",
        headers=_auth(token),
    ).json()
    assert one_day["total"] == 1
    assert one_day["items"][0]["resource_id"] == str(newest.id)
    assert (
        client.get(
            f"{CITIZEN_PATH}?date_from=2026-08-03&date_to=2026-08-01",
            headers=_auth(token),
        ).status_code
        == 422
    )


def test_current_doctor_can_read_history_but_other_contexts_cannot(
    client: TestClient,
    db_session,
    test_settings: Settings,
) -> None:
    facility = _facility(db_session)
    doctor, registration = _professional(db_session, facility)
    citizen = _citizen(db_session, "Current")
    visit = _visit(
        db_session,
        citizen=citizen,
        registration=registration,
        facility=facility,
        finalized_at=datetime(2026, 7, 1, 10, tzinfo=UTC),
        diagnosis="Historical diagnosis",
    )
    _make_current(
        db_session,
        citizen=citizen,
        doctor_registration=registration,
        facility=facility,
    )
    doctor_token = _token(
        db_session,
        test_settings,
        doctor,
        Portal.PROFESSIONAL,
        role_registration_id=registration.id,
    )
    allowed = client.get(PROFESSIONAL_PATH, headers=_auth(doctor_token))
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["items"][0]["resource_id"] == str(visit.id)

    other_doctor, other_registration = _professional(db_session, facility)
    other_token = _token(
        db_session,
        test_settings,
        other_doctor,
        Portal.PROFESSIONAL,
        role_registration_id=other_registration.id,
    )
    assert client.get(PROFESSIONAL_PATH, headers=_auth(other_token)).status_code == 404

    lab_user, lab_registration = _professional(
        db_session, facility, role_code=ProfessionalRoleCode.LAB_TECHNICIAN
    )
    lab_token = _token(
        db_session,
        test_settings,
        lab_user,
        Portal.PROFESSIONAL,
        role_registration_id=lab_registration.id,
    )
    assert client.get(PROFESSIONAL_PATH, headers=_auth(lab_token)).status_code == 403


def test_empty_history_returns_an_empty_page(
    client: TestClient,
    db_session,
    test_settings: Settings,
) -> None:
    citizen = _citizen(db_session, "Empty")
    token = _token(db_session, test_settings, citizen.user, Portal.CITIZEN)
    response = client.get(CITIZEN_PATH, headers=_auth(token))
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "page_size": 20,
        "total": 0,
        "has_next": False,
    }
