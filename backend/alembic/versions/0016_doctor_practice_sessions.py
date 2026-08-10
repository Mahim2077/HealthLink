"""create doctor practice sessions

Revision ID: 0016_doctor_practice_sessions
Revises: 0015_doctor_practice_schedules
Create Date: 2026-08-19

Adds the per-day chamber session that becomes the queue container for
appointments booked against a doctor at a given facility. The session row
is created lazily when the first appointment is booked for the day or
explicitly when the doctor starts practice.

The unique key (doctor_role_registration_id, facility_id, session_date)
guarantees a single chamber session per doctor per facility per date,
matching V6 section 18.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0016_doctor_practice_sessions"
down_revision: str | None = "0015_doctor_practice_schedules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "doctor_practice_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "doctor_role_registration_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "facility_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="NOT_STARTED",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('NOT_STARTED','ACTIVE','COMPLETED')",
            name=op.f("ck_doctor_practice_sessions_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["doctor_role_registration_id"],
            ["professional_role_registrations.id"],
            name=op.f(
                "fk_doctor_practice_sessions_doctor_role_registration_id_prof_role_reg"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["facility_id"],
            ["healthcare_facilities.id"],
            name=op.f(
                "fk_doctor_practice_sessions_facility_id_healthcare_facilities"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_doctor_practice_sessions")
        ),
        sa.UniqueConstraint(
            "doctor_role_registration_id",
            "facility_id",
            "session_date",
            name=op.f(
                "uq_doctor_practice_sessions_doctor_role_reg_facility_date"
            ),
        ),
    )
    op.create_index(
        "ix_doctor_practice_sessions_doctor_role_registration_id",
        "doctor_practice_sessions",
        ["doctor_role_registration_id"],
        unique=False,
    )
    op.create_index(
        "ix_doctor_practice_sessions_facility_id",
        "doctor_practice_sessions",
        ["facility_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_doctor_practice_sessions_facility_id",
        table_name="doctor_practice_sessions",
    )
    op.drop_index(
        "ix_doctor_practice_sessions_doctor_role_registration_id",
        table_name="doctor_practice_sessions",
    )
    op.drop_table("doctor_practice_sessions")