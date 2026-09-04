"""create prescriptions

Revision ID: 0021_prescriptions
Revises: 0020_medical_visits
Create Date: 2026-08-21

Adds the chamber prescription header table from V6 section 26. Each
prescription is bound to a single medical visit (UNIQUE constraint) and
to the doctor role registration that authored it. Prescriptions remain
mutable by the author doctor even after the visit is finalized — that
intentional exception to ordinary finalized-record immutability is what
allows the author doctor to make later corrections. Phase 14 appointment
closure does not revoke this documented author-only edit permission.

The PDF that represents a prescription is rendered from the structured
fields by ``app/prescriptions/pdf.py`` and stored in private
object-storage backed by ``app/prescriptions/storage.py``.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0021_prescriptions"
down_revision: str | None = "0020_medical_visits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prescriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "visit_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "citizen_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "author_doctor_role_registration_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "diagnostic_information", sa.Text(), nullable=True
        ),
        sa.Column("medical_advice", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["visit_id"],
            ["medical_visits.id"],
            name=op.f("fk_prescriptions_visit_id_medical_visits"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["citizen_id"],
            ["citizen_profiles.id"],
            name=op.f("fk_prescriptions_citizen_id_citizen_profiles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["author_doctor_role_registration_id"],
            ["professional_role_registrations.id"],
            name=op.f(
                "fk_prescriptions_author_doctor_role_reg_id_prof_role_reg"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prescriptions")),
        sa.UniqueConstraint(
            "visit_id",
            name=op.f("uq_prescriptions_visit_id"),
        ),
    )
    op.create_index(
        "ix_prescriptions_citizen_id",
        "prescriptions",
        ["citizen_id"],
        unique=False,
    )
    op.create_index(
        "ix_prescriptions_author_doctor_role_registration_id",
        "prescriptions",
        ["author_doctor_role_registration_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prescriptions_author_doctor_role_registration_id",
        table_name="prescriptions",
    )
    op.drop_index(
        "ix_prescriptions_citizen_id", table_name="prescriptions"
    )
    op.drop_table("prescriptions")
