"""Add email verification and password recovery challenges."""

import sqlalchemy as sa
from alembic import op


revision = "0032_auth_email_codes"
down_revision = "0031_ai_conversations"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True)))
    op.create_table(
        "auth_email_code_challenges",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("scope_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("account_hash", sa.String(64)),
        sa.Column("code_hash", sa.String(64)),
        sa.Column("reset_hash", sa.String(64)),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("scope_hash", "user_id", "expires_at"):
        op.create_index(f"ix_auth_email_code_challenges_{column}", "auth_email_code_challenges", [column])
    op.create_table(
        "auth_email_code_limits",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_email_code_limits_expires_at", "auth_email_code_limits", ["expires_at"])


def downgrade():
    op.drop_table("auth_email_code_limits")
    op.drop_table("auth_email_code_challenges")
    op.drop_column("users", "email_verified_at")
