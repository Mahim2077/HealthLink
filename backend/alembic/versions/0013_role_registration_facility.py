"""link professional role registrations to facilities

Revision ID: 0013_role_facility_fk
Revises: 0012_facilities
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0013_role_facility_fk"
down_revision: str | None = "0012_facilities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "professional_role_registrations",
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_prof_role_regs_facility_id_facilities",
        "professional_role_registrations",
        "healthcare_facilities",
        ["facility_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_prof_role_regs_facility_id_facilities",
        "professional_role_registrations",
        type_="foreignkey",
    )
    op.drop_column("professional_role_registrations", "facility_id")
