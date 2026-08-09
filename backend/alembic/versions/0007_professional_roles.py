"""create and seed professional roles

Revision ID: 0007_prof_roles
Revises: 0006_prof_profiles
Create Date: 2026-08-10
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0007_prof_roles"
down_revision: str | None = "0006_prof_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_ROWS = (
    ("10000000-0000-0000-0000-000000000001", "DOCTOR", "Doctor", "Registered medical doctor"),
    ("10000000-0000-0000-0000-000000000002", "LAB_TECHNICIAN", "Lab Technician", "Diagnostic laboratory professional"),
    ("10000000-0000-0000-0000-000000000003", "NURSE", "Nurse", "Nursing professional"),
    ("10000000-0000-0000-0000-000000000004", "PHARMACIST", "Pharmacist", "Pharmacy professional"),
    ("10000000-0000-0000-0000-000000000005", "RADIOLOGY_TECHNICIAN", "Radiology Technician", "Radiology and imaging professional"),
    ("10000000-0000-0000-0000-000000000006", "OTHER_HEALTHCARE_PROFESSIONAL", "Other Healthcare Professional", "Other healthcare professional role"),
)


def upgrade() -> None:
    roles = op.create_table(
        "professional_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_professional_roles"),
        sa.UniqueConstraint("code", name="uq_professional_roles_code"),
    )
    op.bulk_insert(
        roles,
        [
            {"id": uuid.UUID(role_id), "code": code, "name": name, "description": description, "is_active": True}
            for role_id, code, name, description in ROLE_ROWS
        ],
    )


def downgrade() -> None:
    op.drop_table("professional_roles")
