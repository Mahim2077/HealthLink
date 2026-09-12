"""create structured diagnostic tests

Revision ID: 0024_diagnostic_tests
Revises: 0023_prescription_documents
Create Date: 2026-09-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0024_diagnostic_tests"
down_revision: str | None = "0023_prescription_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "diagnostic_tests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("citizen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_by_role_registration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_to_role_registration_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("test_name", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="REQUESTED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('REQUESTED','IN_PROGRESS','COMPLETED','CANCELLED')", name=op.f("ck_diagnostic_tests_valid_status")),
        sa.ForeignKeyConstraint(["citizen_id"], ["citizen_profiles.id"], name=op.f("fk_diagnostic_tests_citizen_id_citizen_profiles"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["visit_id"], ["medical_visits.id"], name=op.f("fk_diagnostic_tests_visit_id_medical_visits"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_role_registration_id"], ["professional_role_registrations.id"], name=op.f("fk_diagnostic_tests_requested_by_role_registration_id_professional_role_registrations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_to_role_registration_id"], ["professional_role_registrations.id"], name=op.f("fk_diagnostic_tests_assigned_to_role_registration_id_professional_role_registrations"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["facility_id"], ["healthcare_facilities.id"], name=op.f("fk_diagnostic_tests_facility_id_healthcare_facilities"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnostic_tests")),
    )
    op.create_index("ix_diagnostic_tests_citizen_id", "diagnostic_tests", ["citizen_id"])
    op.create_index("ix_diagnostic_tests_requested_by", "diagnostic_tests", ["requested_by_role_registration_id"])
    op.create_index("ix_diagnostic_tests_assigned_to_status", "diagnostic_tests", ["assigned_to_role_registration_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_diagnostic_tests_assigned_to_status", table_name="diagnostic_tests")
    op.drop_index("ix_diagnostic_tests_requested_by", table_name="diagnostic_tests")
    op.drop_index("ix_diagnostic_tests_citizen_id", table_name="diagnostic_tests")
    op.drop_table("diagnostic_tests")
