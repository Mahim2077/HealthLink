"""create patient access grants

Revision ID: 0019_patient_access_grants
Revises: 0018_appointment_queue_entries
Create Date: 2026-08-19

Adds the manual patient->professional access grant table from V6
section 24. Phase 12 only needs the existence of the table so the
``require_current_patient_access`` dependency can recognise a valid
pre-existing grant when present; no Phase 12 route mutates grants.

A grant is active when ``revoked_at IS NULL`` and (``expires_at``
is NULL or in the future). The partial index makes that lookup
fast and avoids returning revoked rows to the access dependency.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0019_patient_access_grants"
down_revision: str | None = "0018_appointment_queue_entries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patient_access_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "citizen_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "professional_role_registration_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("access_scope", sa.String(length=50), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["citizen_id"],
            ["citizen_profiles.id"],
            name=op.f("fk_patient_access_grants_citizen_id_citizen_profiles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["professional_role_registration_id"],
            ["professional_role_registrations.id"],
            name=op.f(
                "fk_patient_access_grants_prof_role_reg_prof_role_registrations"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_patient_access_grants")
        ),
        sa.CheckConstraint(
            "access_scope IN ('FULL_RECORD','LIMITED')",
            name=op.f("ck_patient_access_grants_valid_scope"),
        ),
    )
    op.create_index(
        "ix_patient_access_grants_citizen_id",
        "patient_access_grants",
        ["citizen_id"],
        unique=False,
    )
    op.create_index(
        "ix_patient_access_grants_professional_role_registration_id",
        "patient_access_grants",
        ["professional_role_registration_id"],
        unique=False,
    )
    # PostgreSQL partial index for "currently active grants" lookups used by
    # require_current_patient_access. SQLite ignores partial index syntax.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX ix_patient_access_grants_active "
            "ON patient_access_grants (citizen_id, professional_role_registration_id) "
            "WHERE revoked_at IS NULL"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP INDEX IF EXISTS ix_patient_access_grants_active"
        )
    op.drop_index(
        "ix_patient_access_grants_professional_role_registration_id",
        table_name="patient_access_grants",
    )
    op.drop_index(
        "ix_patient_access_grants_citizen_id",
        table_name="patient_access_grants",
    )
    op.drop_table("patient_access_grants")