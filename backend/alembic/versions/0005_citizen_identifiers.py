"""create citizen identity links

Revision ID: 0005_citizen_identifiers
Revises: 0004_citizen_profiles
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005_citizen_identifiers"
down_revision: str | None = "0004_citizen_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "citizen_identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "national_identifier_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "birth_certificate_number",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column("registered_with", sa.String(length=32), nullable=False),
        sa.Column("nid_added_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "national_identifier_id IS NOT NULL OR birth_certificate_number IS NOT NULL",
            name=op.f("ck_citizen_identifiers_identity_present"),
        ),
        sa.CheckConstraint(
            "registered_with IN ('NID', 'BCN')",
            name=op.f("ck_citizen_identifiers_valid_registered_with"),
        ),
        sa.ForeignKeyConstraint(
            ["national_identifier_id"],
            ["user_national_identifiers.id"],
            name=op.f(
                "fk_citizen_identifiers_national_identifier_id_user_national_identifiers"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_citizen_identifiers_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_citizen_identifiers"),
        sa.UniqueConstraint(
            "birth_certificate_number",
            name="uq_citizen_identifiers_birth_certificate_number",
        ),
        sa.UniqueConstraint(
            "national_identifier_id",
            name="uq_citizen_identifiers_national_identifier_id",
        ),
        sa.UniqueConstraint("user_id", name="uq_citizen_identifiers_user_id"),
    )


def downgrade() -> None:
    op.drop_table("citizen_identifiers")
