"""create doctor registration details

Revision ID: 0009_doctor_reg_details
Revises: 0008_prof_role_regs
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0009_doctor_reg_details"
down_revision: str | None = "0008_prof_role_regs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "doctor_registration_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_role_registration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bmdc_registration_number", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["professional_role_registration_id"], ["professional_role_registrations.id"], name=op.f("fk_doctor_registration_details_professional_role_registration_id_professional_role_registrations"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_registration_details"),
        sa.UniqueConstraint("bmdc_registration_number", name="uq_doctor_registration_details_bmdc_registration_number"),
        sa.UniqueConstraint("professional_role_registration_id", name=op.f("uq_doctor_registration_details_professional_role_registration_id")),
    )


def downgrade() -> None:
    op.drop_table("doctor_registration_details")
