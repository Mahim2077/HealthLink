from __future__ import annotations

from dataclasses import dataclass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admins.models import AdminAccount
from app.admins.repository import AdminRepository
from app.auth.models import User
from app.core.security import hash_password


class AdminProvisioningError(ValueError):
    pass


@dataclass(frozen=True)
class ProvisionedAdmin:
    user: User
    admin: AdminAccount


def create_trusted_admin(
    db: Session,
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    is_super_admin: bool = False,
) -> ProvisionedAdmin:
    normalized_email = str(TypeAdapter(EmailStr).validate_python(email)).strip().lower()
    first_name = first_name.strip()
    last_name = last_name.strip()
    if not first_name or len(first_name) > 100:
        raise AdminProvisioningError("First name must contain 1–100 characters.")
    if not last_name or len(last_name) > 100:
        raise AdminProvisioningError("Last name must contain 1–100 characters.")
    if len(password) < 12 or len(password) > 128:
        raise AdminProvisioningError("Admin password must contain 12–128 characters.")
    repository = AdminRepository(db)
    if repository.get_user_by_email(normalized_email) is not None:
        raise AdminProvisioningError("A HealthLink user already uses this email.")

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
    )
    try:
        repository.add(user)
        db.flush()
        admin = AdminAccount(user_id=user.id, is_super_admin=is_super_admin)
        repository.add(admin)
        db.commit()
        db.refresh(user)
        db.refresh(admin)
        return ProvisionedAdmin(user=user, admin=admin)
    except IntegrityError as error:
        db.rollback()
        raise AdminProvisioningError("Admin account could not be created.") from error
    except Exception:
        db.rollback()
        raise
