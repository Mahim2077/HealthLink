"""add active professional role to auth sessions

Revision ID: 0014_auth_active_role
Revises: 0013_role_facility_fk
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0014_auth_active_role"
down_revision: str | None = "0013_role_facility_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column(
            "active_professional_role_registration_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_auth_sessions_active_prof_role",
        "auth_sessions",
        "professional_role_registrations",
        ["active_professional_role_registration_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_auth_sessions_active_prof_role", "auth_sessions", type_="foreignkey"
    )
    op.drop_column("auth_sessions", "active_professional_role_registration_id")
