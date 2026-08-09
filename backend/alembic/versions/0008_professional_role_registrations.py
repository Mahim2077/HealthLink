"""create professional role registrations

Revision ID: 0008_prof_role_regs
Revises: 0007_prof_roles
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0008_prof_role_regs"
down_revision: str | None = "0007_prof_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "professional_role_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_name_submitted", sa.String(length=255), nullable=False),
        sa.Column("designation", sa.String(length=150), nullable=False),
        sa.Column("additional_info", sa.Text(), nullable=True),
        sa.Column("verification_status", sa.String(length=32), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("verification_status IN ('PENDING', 'VERIFIED', 'REJECTED')", name=op.f("ck_professional_role_registrations_valid_verification_status")),
        sa.ForeignKeyConstraint(["professional_id"], ["healthcare_professional_profiles.id"], name=op.f("fk_professional_role_registrations_professional_id_healthcare_professional_profiles"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["role_id"], ["professional_roles.id"], name="fk_professional_role_registrations_role_id_professional_roles", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"], name="fk_professional_role_registrations_verified_by_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_professional_role_registrations"),
        sa.UniqueConstraint("professional_id", "role_id", name="uq_professional_role_registrations_professional_id"),
    )
    op.create_index(
        "ix_prof_role_regs_prof_role_status",
        "professional_role_registrations",
        ["professional_id", "role_id", "verification_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_prof_role_regs_prof_role_status", table_name="professional_role_registrations")
    op.drop_table("professional_role_registrations")
