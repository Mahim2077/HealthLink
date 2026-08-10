"""create appointments

Revision ID: 0017_appointments
Revises: 0016_doctor_practice_sessions
Create Date: 2026-08-19

Implements the serial-based appointment model defined in V6 section 15.
The composite unique key (doctor_role_registration_id, facility_id,
appointment_date, serial_number) is the database-level guarantee that
serials are unique per day per doctor per facility; the service layer
extends it with advisory locking for concurrent booking (V6 section 17).

``status`` is constrained to the V6 status set: BOOKED, CANCELLED,
COMPLETED, REMOVED_BY_DOCTOR, NO_SHOW. Historical rows are never
hard-deleted so the chamber queue and audit trail stay intact.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0017_appointments"
down_revision: str | None = "0016_doctor_practice_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "citizen_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
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
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("serial_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("booked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('BOOKED','CANCELLED','COMPLETED',"
            "'REMOVED_BY_DOCTOR','NO_SHOW')",
            name=op.f("ck_appointments_valid_status"),
        ),
        sa.CheckConstraint(
            "serial_number >= 1",
            name=op.f("ck_appointments_serial_number_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["citizen_id"],
            ["citizen_profiles.id"],
            name=op.f("fk_appointments_citizen_id_citizen_profiles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_role_registration_id"],
            ["professional_role_registrations.id"],
            name=op.f(
                "fk_appointments_doctor_role_registration_id_prof_role_reg"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["facility_id"],
            ["healthcare_facilities.id"],
            name=op.f("fk_appointments_facility_id_healthcare_facilities"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appointments")),
        sa.UniqueConstraint(
            "doctor_role_registration_id",
            "facility_id",
            "appointment_date",
            "serial_number",
            name=op.f("uq_appointments_doctor_role_reg_facility_date_serial"),
        ),
    )
    op.create_index(
        "ix_appointments_citizen_id",
        "appointments",
        ["citizen_id"],
        unique=False,
    )
    op.create_index(
        "ix_appointments_doctor_role_registration_id",
        "appointments",
        ["doctor_role_registration_id"],
        unique=False,
    )
    op.create_index(
        "ix_appointments_facility_id",
        "appointments",
        ["facility_id"],
        unique=False,
    )
    op.create_index(
        "ix_appointments_status",
        "appointments",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index(
        "ix_appointments_doctor_role_registration_id",
        table_name="appointments",
    )
    op.drop_index("ix_appointments_facility_id", table_name="appointments")
    op.drop_index("ix_appointments_citizen_id", table_name="appointments")
    op.drop_table("appointments")
