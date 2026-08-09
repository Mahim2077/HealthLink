"""create authoritative national identifiers

Revision ID: 0003_user_national_identifiers
Revises: 0002_auth_sessions
Create Date: 2026-08-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_user_national_identifiers"
down_revision: str | None = "0002_auth_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_national_identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nid_number", sa.String(length=32), nullable=False),
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
            name="fk_user_national_identifiers_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_national_identifiers"),
        sa.UniqueConstraint(
            "nid_number",
            name="uq_user_national_identifiers_nid_number",
        ),
        sa.UniqueConstraint(
            "user_id",
            name="uq_user_national_identifiers_user_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("user_national_identifiers")
