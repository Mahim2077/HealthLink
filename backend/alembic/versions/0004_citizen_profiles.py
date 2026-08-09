"""create citizen profiles

Revision ID: 0004_citizen_profiles
Revises: 0003_user_national_identifiers
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0004_citizen_profiles"
down_revision: str | None = "0003_user_national_identifiers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "citizen_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=32), nullable=False),
        sa.Column("blood_group", sa.String(length=8), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_citizen_profiles_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_citizen_profiles"),
        sa.UniqueConstraint("user_id", name="uq_citizen_profiles_user_id"),
    )


def downgrade() -> None:
    op.drop_table("citizen_profiles")
