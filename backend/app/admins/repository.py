from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admins.models import AdminAccount
from app.auth.models import User


class AdminRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def get_admin_by_user_id(self, user_id: uuid.UUID) -> AdminAccount | None:
        return self.db.scalar(
            select(AdminAccount).where(AdminAccount.user_id == user_id)
        )

    def add(self, instance):
        self.db.add(instance)
        return instance
