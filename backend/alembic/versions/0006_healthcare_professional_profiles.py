"""create healthcare professional profiles

Revision ID: 0006_prof_profiles
Revises: 0005_citizen_identifiers
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0006_prof_profiles"
down_revision: str | None = "0005_citizen_identifiers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "healthcare_professional_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_healthcare_professional_profiles_user_id_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_healthcare_professional_profiles"),
        sa.UniqueConstraint("user_id", name="uq_healthcare_professional_profiles_user_id"),
    )


def downgrade() -> None:
    op.drop_table("healthcare_professional_profiles")
