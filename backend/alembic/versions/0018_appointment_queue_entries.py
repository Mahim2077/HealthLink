"""create appointment queue entries

Revision ID: 0018_appointment_queue_entries
Revises: 0017_appointments
Create Date: 2026-08-19

Adds the per-appointment queue row that drives the doctor chamber queue
(V6 section 19). The serial number is owned by the parent ``appointments``
row and is read by joining; this table only tracks the queue lifecycle,
``became_current_at`` audit timestamps, and removal bookkeeping.

The PostgreSQL partial unique index
``uq_one_current_queue_entry_per_session`` enforces at most one CURRENT row
per ``practice_session_id`` at the database level, which is the safety net
for the advancing queue semantics in V6 section 20.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0018_appointment_queue_entries"
down_revision: str | None = "0017_appointments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "appointment_queue_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "practice_session_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "queue_status",
            sa.String(length=32),
            nullable=False,
            server_default="WAITING",
        ),
        sa.Column(
            "became_current_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
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
            "queue_status IN ('WAITING','CURRENT','SKIPPED','DONE',"
            "'REMOVED','CANCELLED')",
            name=op.f("ck_appointment_queue_entries_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name=op.f(
                "fk_appointment_queue_entries_appointment_id_appointments"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["practice_session_id"],
            ["doctor_practice_sessions.id"],
            name=op.f(
                "fk_appointment_queue_entries_practice_session_id_doctor_practice_sessions"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_appointment_queue_entries")
        ),
        sa.UniqueConstraint(
            "appointment_id",
            name=op.f("uq_appointment_queue_entries_appointment_id"),
        ),
    )
    op.create_index(
        "ix_appointment_queue_entries_practice_session_id",
        "appointment_queue_entries",
        ["practice_session_id"],
        unique=False,
    )
    op.create_index(
        "ix_appointment_queue_entries_queue_status",
        "appointment_queue_entries",
        ["queue_status"],
        unique=False,
    )
    # PostgreSQL partial unique index: at most one CURRENT queue entry per
    # doctor chamber session. SQLite compiled into the same Python binary
    # build does not support partial indexes, so skip it there; the service
    # layer still enforces the invariant in the application transaction.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE UNIQUE INDEX "
            "uq_one_current_queue_entry_per_session "
            "ON appointment_queue_entries (practice_session_id) "
            "WHERE queue_status = 'CURRENT'"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP INDEX IF EXISTS uq_one_current_queue_entry_per_session"
        )
    op.drop_index(
        "ix_appointment_queue_entries_queue_status",
        table_name="appointment_queue_entries",
    )
    op.drop_index(
        "ix_appointment_queue_entries_practice_session_id",
        table_name="appointment_queue_entries",
    )
    op.drop_table("appointment_queue_entries")
