"""create medical visits

Revision ID: 0020_medical_visits
Revises: 0019_patient_access_grants
Create Date: 2026-08-19

Adds the chamber consultation workspace table from V6 section 25.
Each visit is linked to a citizen, the doctor role registration that
authored it, the facility, and at most one appointment. Only the
current appointment doctor may create a visit; Phase 14 finalises the
visit when the appointment finishes.

``appointment_id`` is UNIQUE so the queue invariant
"at most one visit per appointment" is enforced at the database
level, and a partial index on ``status = 'DRAFT'`` speeds up the
"open consultation for the current patient" lookup.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0020_medical_visits"
down_revision: str | None = "0019_patient_access_grants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "medical_visits",
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
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "visit_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("follow_up_instructions", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "finalized_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
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
            "status IN ('DRAFT','FINALIZED')",
            name=op.f("ck_medical_visits_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["citizen_id"],
            ["citizen_profiles.id"],
            name=op.f("fk_medical_visits_citizen_id_citizen_profiles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_role_registration_id"],
            ["professional_role_registrations.id"],
            name=op.f(
                "fk_medical_visits_doctor_role_registration_id_prof_role_reg"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["facility_id"],
            ["healthcare_facilities.id"],
            name=op.f("fk_medical_visits_facility_id_healthcare_facilities"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name=op.f("fk_medical_visits_appointment_id_appointments"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medical_visits")),
        sa.UniqueConstraint(
            "appointment_id",
            name=op.f("uq_medical_visits_appointment_id"),
        ),
    )
    op.create_index(
        "ix_medical_visits_citizen_id",
        "medical_visits",
        ["citizen_id"],
        unique=False,
    )
    op.create_index(
        "ix_medical_visits_doctor_role_registration_id",
        "medical_visits",
        ["doctor_role_registration_id"],
        unique=False,
    )
    op.create_index(
        "ix_medical_visits_facility_id",
        "medical_visits",
        ["facility_id"],
        unique=False,
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_medical_visits_draft "
            "ON medical_visits (citizen_id, doctor_role_registration_id) "
            "WHERE status = 'DRAFT'"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_medical_visits_draft")
    op.drop_index(
        "ix_medical_visits_facility_id", table_name="medical_visits"
    )
    op.drop_index(
        "ix_medical_visits_doctor_role_registration_id",
        table_name="medical_visits",
    )
    op.drop_index(
        "ix_medical_visits_citizen_id", table_name="medical_visits"
    )
    op.drop_table("medical_visits")