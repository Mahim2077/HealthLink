from collections.abc import Callable
from datetime import date

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.constants import Portal
from app.auth.models import AuthSession, User
from app.auth.service import AuthenticationError
from app.citizens.constants import CitizenRegistrationMethod
from app.citizens.models import (
    CitizenIdentifier,
    CitizenProfile,
    UserNationalIdentifier,
)
from app.citizens.schemas import CitizenLoginRequest, CitizenRegistrationRequest
from app.citizens.service import (
    _DUMMY_PASSWORD_HASH,
    CitizenConflictError,
    CitizenRegistrationError,
    CitizenService,
)
from app.core.config import Settings
from app.core.security import decode_access_token, hash_password, verify_password


def registration_request(
    *,
    email: str = "citizen@example.com",
    nid_number: str | None = "1234567890",
    birth_certificate_number: str | None = None,
) -> CitizenRegistrationRequest:
    return CitizenRegistrationRequest(
        email=email,
        password="StrongPassword123!",
        first_name="Amina",
        last_name="Rahman",
        date_of_birth=date(1995, 5, 20),
        gender="FEMALE",
        blood_group="A+",
        address="Dhaka",
        nid_number=nid_number,
        birth_certificate_number=birth_certificate_number,
    )


def test_nid_registration_is_transactional_and_hashes_password(
    db_session: Session,
    test_settings: Settings,
) -> None:
    service = CitizenService(db_session, test_settings)

    registered = service.register(registration_request())

    assert registered.identity.registered_with == CitizenRegistrationMethod.NID.value
    assert registered.identity.birth_certificate_number is None
    assert registered.identity.national_identifier_id is not None
    national_identifier = db_session.get(
        UserNationalIdentifier,
        registered.identity.national_identifier_id,
    )
    assert national_identifier is not None
    assert national_identifier.nid_number == "1234567890"
    assert verify_password("StrongPassword123!", registered.user.password_hash)
    assert registered.user.password_hash != "StrongPassword123!"
    assert db_session.scalar(select(func.count()).select_from(AuthSession)) == 0


def test_bcn_registration_uses_citizen_only_identity_storage(
    db_session: Session,
    test_settings: Settings,
) -> None:
    registered = CitizenService(db_session, test_settings).register(
        registration_request(
            nid_number=None,
            birth_certificate_number="BCN-2001-00001",
        )
    )

    assert registered.identity.registered_with == CitizenRegistrationMethod.BCN.value
    assert registered.identity.birth_certificate_number == "BCN-2001-00001"
    assert registered.identity.national_identifier_id is None
    assert db_session.scalar(
        select(func.count()).select_from(UserNationalIdentifier)
    ) == 0


def test_schema_and_service_both_enforce_initial_identity_xor(
    test_settings: Settings,
    db_session: Session,
) -> None:
    with pytest.raises(ValidationError):
        registration_request(nid_number=None, birth_certificate_number=None)
    with pytest.raises(ValidationError):
        registration_request(birth_certificate_number="BCN-BOTH")

    bypassed_schema = CitizenRegistrationRequest.model_construct(
        email="bypass@example.com",
        password=SecretStr("StrongPassword123!"),
        first_name="Bypass",
        last_name="Attempt",
        date_of_birth=date(1990, 1, 1),
        gender="OTHER",
        blood_group=None,
        address=None,
        nid_number="NID-BOTH",
        birth_certificate_number="BCN-BOTH",
    )
    with pytest.raises(CitizenRegistrationError):
        CitizenService(db_session, test_settings).register(bypassed_schema)


def test_duplicate_email_nid_and_bcn_are_rejected(
    db_session: Session,
    test_settings: Settings,
) -> None:
    service = CitizenService(db_session, test_settings)
    service.register(registration_request())

    with pytest.raises(CitizenConflictError):
        service.register(
            registration_request(
                email="CITIZEN@example.com",
                nid_number="DIFFERENT-NID",
            )
        )
    with pytest.raises(CitizenConflictError):
        service.register(
            registration_request(
                email="other@example.com",
                nid_number="1234567890",
            )
        )

    service.register(
        registration_request(
            email="bcn@example.com",
            nid_number=None,
            birth_certificate_number="BCN-DUPLICATE",
        )
    )
    with pytest.raises(CitizenConflictError):
        service.register(
            registration_request(
                email="other-bcn@example.com",
                nid_number=None,
                birth_certificate_number="BCN-DUPLICATE",
            )
        )
    assert service.repository.get_user_by_email("other-bcn@example.com") is None


def test_database_conflict_rolls_back_entire_registration(
    db_session: Session,
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CitizenService(db_session, test_settings)
    service.register(registration_request())
    monkeypatch.setattr(
        service.repository,
        "get_national_identifier_by_number",
        lambda _nid_number: None,
    )

    with pytest.raises(CitizenConflictError):
        service.register(
            registration_request(
                email="race-loser@example.com",
                nid_number="1234567890",
            )
        )

    assert service.repository.get_user_by_email("race-loser@example.com") is None


def test_login_requires_valid_password_active_user_and_citizen_profile(
    db_session: Session,
    test_settings: Settings,
    user_factory: Callable[..., User],
) -> None:
    service = CitizenService(db_session, test_settings)
    registered = service.register(registration_request())

    issued = service.login(
        CitizenLoginRequest(
            email="CITIZEN@example.com",
            password="StrongPassword123!",
        )
    )
    claims = decode_access_token(issued.access_token, test_settings)
    assert claims.sub == registered.user.id
    assert claims.portal is Portal.CITIZEN

    with pytest.raises(AuthenticationError):
        service.login(
            CitizenLoginRequest(email="citizen@example.com", password="x")
        )

    registered.user.is_active = False
    db_session.commit()
    with pytest.raises(AuthenticationError):
        service.login(
            CitizenLoginRequest(
                email="citizen@example.com",
                password="StrongPassword123!",
            )
        )

    noncitizen = User(
        email="noncitizen@example.com",
        password_hash=hash_password("StrongPassword123!"),
        first_name="Not",
        last_name="Citizen",
    )
    db_session.add(noncitizen)
    db_session.commit()
    with pytest.raises(AuthenticationError):
        service.login(
            CitizenLoginRequest(
                email="noncitizen@example.com",
                password="StrongPassword123!",
            )
        )


def test_login_always_performs_exactly_one_argon2_verification(
    db_session: Session,
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CitizenService(db_session, test_settings)
    citizen = service.register(registration_request())
    profileless = User(
        email="profileless@example.com",
        password_hash=hash_password("StrongPassword123!"),
        first_name="No",
        last_name="Profile",
    )
    db_session.add(profileless)
    db_session.commit()

    verification_hashes: list[str] = []

    def record_verification(_password: str, password_hash: str) -> bool:
        verification_hashes.append(password_hash)
        return True

    monkeypatch.setattr(
        "app.citizens.service.verify_password",
        record_verification,
    )

    with pytest.raises(AuthenticationError):
        service.login(
            CitizenLoginRequest(email="unknown@example.com", password="x")
        )
    assert verification_hashes == [_DUMMY_PASSWORD_HASH]

    issued = service.login(
        CitizenLoginRequest(
            email="citizen@example.com",
            password="StrongPassword123!",
        )
    )
    assert issued.portal is Portal.CITIZEN
    assert verification_hashes == [
        _DUMMY_PASSWORD_HASH,
        citizen.user.password_hash,
    ]

    citizen.user.is_active = False
    db_session.commit()
    with pytest.raises(AuthenticationError):
        service.login(
            CitizenLoginRequest(
                email="citizen@example.com",
                password="StrongPassword123!",
            )
        )
    with pytest.raises(AuthenticationError):
        service.login(
            CitizenLoginRequest(
                email="profileless@example.com",
                password="StrongPassword123!",
            )
        )

    assert verification_hashes == [
        _DUMMY_PASSWORD_HASH,
        citizen.user.password_hash,
        citizen.user.password_hash,
        profileless.password_hash,
    ]
    assert db_session.scalar(select(func.count()).select_from(AuthSession)) == 1


def test_login_dummy_hash_is_a_valid_precomputed_argon2id_hash() -> None:
    assert _DUMMY_PASSWORD_HASH.startswith("$argon2id$")
    assert verify_password(
        "HealthLink-login-dummy-password",
        _DUMMY_PASSWORD_HASH,
    )


def test_identity_details_are_scoped_by_user(
    db_session: Session,
    test_settings: Settings,
) -> None:
    service = CitizenService(db_session, test_settings)
    nid_citizen = service.register(registration_request())
    bcn_citizen = service.register(
        registration_request(
            email="second@example.com",
            nid_number=None,
            birth_certificate_number="BCN-SECOND",
        )
    )

    nid_details = service.get_identity(nid_citizen.user.id)
    bcn_details = service.get_identity(bcn_citizen.user.id)

    assert nid_details.national_identifier is not None
    assert nid_details.national_identifier.nid_number == "1234567890"
    assert bcn_details.national_identifier is None
    assert bcn_details.identity.birth_certificate_number == "BCN-SECOND"
