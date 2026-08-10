"""create doctor practice schedules

Revision ID: 0015_doctor_practice_schedules
Revises: 0014_auth_active_role
Create Date: 2026-08-12

Adds the per-doctor weekly availability windows used by the doctor discovery
and practice schedule endpoints defined in V6 sections 13 and 14. Each row
binds a verified doctor's user account to a single healthcare facility and a
weekday window with a per-day patient cap. Soft deletion is driven by the
``deleted_at`` column so historical rows remain observable.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0015_doctor_practice_schedules"
down_revision: str | None = "0014_auth_active_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "doctor_practice_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "doctor_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "facility_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("weekday", sa.String(length=16), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("max_patients", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
            "weekday IN ('MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY')",
            name=op.f("ck_doctor_practice_schedules_valid_weekday"),
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE','INACTIVE')",
            name=op.f("ck_doctor_practice_schedules_valid_status"),
        ),
        sa.CheckConstraint(
            "max_patients >= 1",
            name=op.f("ck_doctor_practice_schedules_max_patients_positive"),
        ),
        sa.CheckConstraint(
            "end_time > start_time",
            name=op.f("ck_doctor_practice_schedules_end_after_start"),
        ),
        sa.ForeignKeyConstraint(
            ["doctor_user_id"],
            ["users.id"],
            name=op.f("fk_doctor_practice_schedules_doctor_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["facility_id"],
            ["healthcare_facilities.id"],
            name=op.f(
                "fk_doctor_practice_schedules_facility_id_healthcare_facilities"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_doctor_practice_schedules")
        ),
    )
    op.create_index(
        "ix_doctor_practice_schedules_doctor_user_id",
        "doctor_practice_schedules",
        ["doctor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_doctor_practice_schedules_facility_id",
        "doctor_practice_schedules",
        ["facility_id"],
        unique=False,
    )
    op.create_index(
        "ix_doctor_practice_schedules_doctor_user_id_facility_id_weekday",
        "doctor_practice_schedules",
        ["doctor_user_id", "facility_id", "weekday"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_doctor_practice_schedules_doctor_user_id_facility_id_weekday",
        table_name="doctor_practice_schedules",
    )
    op.drop_index(
        "ix_doctor_practice_schedules_facility_id",
        table_name="doctor_practice_schedules",
    )
    op.drop_index(
        "ix_doctor_practice_schedules_doctor_user_id",
        table_name="doctor_practice_schedules",
    )
    op.drop_table("doctor_practice_schedules")
