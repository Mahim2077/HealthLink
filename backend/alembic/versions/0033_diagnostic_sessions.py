"""Add patient-started lab sessions and private PDF revisions."""

import sqlalchemy as sa
from alembic import op


revision = "0033_diagnostic_sessions"
down_revision = "0032_auth_email_codes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("diagnostic_tests", sa.Column("catalog_code", sa.String(40)))
    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("citizen_id", sa.Uuid(), sa.ForeignKey("citizen_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("technician_id", sa.Uuid(), sa.ForeignKey("professional_role_registrations.id", ondelete="RESTRICT")),
        sa.Column("facility_id", sa.Uuid(), sa.ForeignKey("healthcare_facilities.id", ondelete="RESTRICT")),
        sa.Column("catalog_code", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("share_code", sa.String(32), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("attendance_deadline", sa.DateTime(timezone=True)),
        sa.Column("checked_in_at", sa.DateTime(timezone=True)),
        sa.Column("collected_at", sa.DateTime(timezone=True)),
        sa.Column("performed_at", sa.DateTime(timezone=True)),
        sa.Column("closed_reason", sa.String(40)),
        sa.Column("current_report_version", sa.Integer()),
        sa.CheckConstraint("status IN ('REQUESTED','ACCEPTED','CHECKED_IN','COLLECTED','PERFORMED','PUBLISHED','EXPIRED','CANCELLED','UNABLE')", name="status"),
    )
    op.create_index("ix_diagnostic_sessions_citizen_created", "diagnostic_sessions", ["citizen_id", "created_at"])
    op.create_index("ix_diagnostic_sessions_technician_created", "diagnostic_sessions", ["technician_id", "created_at"])
    op.create_table(
        "diagnostic_session_pdfs",
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("diagnostic_sessions.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("catalog_code", sa.String(40), nullable=False),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
    )
    op.create_index("ix_diagnostic_session_pdfs_catalog_time", "diagnostic_session_pdfs", ["catalog_code", "tested_at"])


def downgrade():
    op.drop_table("diagnostic_session_pdfs")
    op.drop_table("diagnostic_sessions")
    op.drop_column("diagnostic_tests", "catalog_code")
