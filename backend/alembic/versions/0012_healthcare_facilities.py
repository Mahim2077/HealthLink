"""create healthcare facilities

Revision ID: 0012_facilities
Revises: 0011_admin_action_logs
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0012_facilities"
down_revision: str | None = "0011_admin_action_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "healthcare_facilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("facility_type", sa.String(length=50), nullable=False),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "facility_type IN ('HOSPITAL', 'CLINIC', 'DIAGNOSTIC_CENTER', 'PHARMACY')",
            name=op.f("ck_healthcare_facilities_valid_facility_type"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_healthcare_facilities")),
    )
    op.create_index(
        "ix_healthcare_facilities_name",
        "healthcare_facilities",
        ["name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_healthcare_facilities_name", table_name="healthcare_facilities")
    op.drop_table("healthcare_facilities")
