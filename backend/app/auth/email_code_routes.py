import asyncio
import unicodedata
import uuid
from time import monotonic
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, EmailStr, Field, SecretStr
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.auth.constants import Portal
from app.auth.dependencies import AuthContext, get_current_auth_context, get_request_settings
from app.auth.email_codes import RESEND_SECONDS, EmailCodeDelivery, EmailCodeService
from app.auth.email_delivery import send_auth_email, send_auth_email_in_background
from app.core.config import Settings
from app.core.exceptions import HealthLinkError
from app.db.session import get_db
from app.professionals.constants import ProfessionalRoleCode


router = APIRouter(prefix="/auth/email", tags=["email-auth"])
Db = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_request_settings)]
SignedIn = Annotated[AuthContext, Depends(get_current_auth_context)]


class SignupRequest(BaseModel):
    portal: Literal[Portal.CITIZEN, Portal.PROFESSIONAL]
    email: EmailStr


class ProfessionalResetRequest(BaseModel):
    portal: Literal[Portal.PROFESSIONAL]
    nid_number: Annotated[str, Field(min_length=1, max_length=32, pattern=r"\S")]
    role_code: ProfessionalRoleCode


class EmailResetRequest(BaseModel):
    portal: Literal[Portal.CITIZEN, Portal.ADMIN]
    email: EmailStr


ResetRequest = Annotated[ProfessionalResetRequest | EmailResetRequest, Field(discriminator="portal")]


class CodeProof(BaseModel):
    challenge_id: uuid.UUID
    code: Annotated[str, Field(pattern=r"^[0-9]{6}$")]


class ResetCompletion(BaseModel):
    challenge_id: uuid.UUID
    reset_token: Annotated[SecretStr, Field(min_length=43, max_length=43)]
    password: Annotated[SecretStr, Field(min_length=8, max_length=128)]


class EnrollmentRequest(BaseModel):
    password: Annotated[SecretStr, Field(min_length=1, max_length=128)]


class ChallengeResponse(BaseModel):
    challenge_id: uuid.UUID
    resend_after_seconds: int = RESEND_SECONDS


class ResetGrant(BaseModel):
    reset_token: str


class EmailStatus(BaseModel):
    enabled: bool
    verified: bool
    email: str


def _client_address(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _message(delivery: EmailCodeDelivery) -> str:
    return (
        f"Your HealthLink code is {delivery.code}. It expires in 10 minutes.\n\n"
        "If you did not request this code, you can ignore this email."
    )


@router.post("/signup", status_code=202)
def request_signup_code(payload: SignupRequest, request: Request, db: Db, settings: AppSettings) -> ChallengeResponse:
    service = EmailCodeService(db, settings)
    service.check_request_rate(_client_address(request))
    delivery = service.start_signup(str(payload.email).lower(), payload.portal)
    send_auth_email(settings, delivery.recipient, "Verify your HealthLink email", _message(delivery))
    return ChallengeResponse(challenge_id=delivery.challenge_id)


def _prepare_reset(
    service: EmailCodeService, payload: ResetRequest, client_address: str,
) -> tuple[uuid.UUID, EmailCodeDelivery | None]:
    service.check_request_rate(client_address)
    if isinstance(payload, ProfessionalResetRequest):
        return service.start_reset(payload.portal, payload.nid_number.strip(), payload.role_code)
    return service.start_reset(payload.portal, str(payload.email).lower(), None)


@router.post("/reset", status_code=202)
async def request_reset_code(
    payload: ResetRequest, request: Request, background: BackgroundTasks, db: Db, settings: AppSettings,
) -> ChallengeResponse:
    started = monotonic()
    challenge_id, delivery = await run_in_threadpool(
        _prepare_reset, EmailCodeService(db, settings), payload, _client_address(request),
    )
    # Reduce timing differences between existing and unknown accounts.
    await asyncio.sleep(max(0, 0.35 - (monotonic() - started)))
    if delivery:
        background.add_task(
            send_auth_email_in_background, settings, delivery.recipient,
            "Reset your HealthLink password", _message(delivery),
        )
    return ChallengeResponse(challenge_id=challenge_id)


@router.post("/reset/verify")
def verify_reset_code(payload: CodeProof, db: Db, settings: AppSettings) -> ResetGrant:
    service = EmailCodeService(db, settings)
    service.require_enabled()
    return ResetGrant(reset_token=service.verify_reset(payload.challenge_id, payload.code))


@router.post("/reset/complete", status_code=204)
def complete_reset(
    payload: ResetCompletion, background: BackgroundTasks, db: Db, settings: AppSettings,
) -> None:
    service = EmailCodeService(db, settings)
    service.require_enabled()
    password = payload.password.get_secret_value()
    categories = {unicodedata.category(character) for character in password}
    if not {"Lu", "Ll", "Nd"}.issubset(categories) or not any(
        category.startswith(("P", "S")) for category in categories
    ):
        raise HealthLinkError(
            "Use 8–128 characters, including an uppercase letter, a lowercase letter, a number, and a symbol.",
            status_code=400,
        )
    recipient = service.complete_reset(payload.challenge_id, payload.reset_token.get_secret_value(), password)
    background.add_task(
        send_auth_email_in_background, settings, recipient, "Your HealthLink password was updated",
        "Your HealthLink password was updated and existing sessions were signed out. "
        "If you did not make this change, contact HealthLink support.",
    )


@router.get("/status")
def email_status(context: SignedIn, settings: AppSettings) -> EmailStatus:
    return EmailStatus(
        enabled=settings.auth_email_otp_enabled,
        verified=context.user.email_verified_at is not None,
        email=context.user.email,
    )


@router.post("/enroll", status_code=202)
def request_enrollment_code(
    payload: EnrollmentRequest, request: Request, context: SignedIn, db: Db, settings: AppSettings,
) -> ChallengeResponse:
    service = EmailCodeService(db, settings)
    service.check_request_rate(_client_address(request))
    delivery = service.start_enrollment(context.user, payload.password.get_secret_value())
    send_auth_email(settings, delivery.recipient, "Verify your HealthLink recovery email", _message(delivery))
    return ChallengeResponse(challenge_id=delivery.challenge_id)


@router.post("/enroll/verify", status_code=204)
def verify_enrollment_code(payload: CodeProof, context: SignedIn, db: Db, settings: AppSettings) -> None:
    service = EmailCodeService(db, settings)
    service.require_enabled()
    service.verify_enrollment(context.user.id, payload.challenge_id, payload.code)
