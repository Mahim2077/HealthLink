"""create prescription items

Revision ID: 0022_prescription_items
Revises: 0021_prescriptions
Create Date: 2026-08-21

Adds the per-prescription medicines table from V6 section 27. Each
item is one structured medicine row. There is no UNIQUE constraint on
``(prescription_id, medicine_name)`` because doctors occasionally repeat
medicines with different dosage; the structured form lets the frontend
render a deterministic table when the PDF is regenerated.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0022_prescription_items"
down_revision: str | None = "0021_prescriptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prescription_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "prescription_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "medicine_name", sa.String(length=200), nullable=False
        ),
        sa.Column("dosage", sa.String(length=100), nullable=False),
        sa.Column(
            "frequency", sa.String(length=100), nullable=False
        ),
        sa.Column(
            "duration", sa.String(length=100), nullable=False
        ),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["prescription_id"],
            ["prescriptions.id"],
            name=op.f(
                "fk_prescription_items_prescription_id_prescriptions"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_prescription_items")
        ),
    )
    op.create_index(
        "ix_prescription_items_prescription_id",
        "prescription_items",
        ["prescription_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prescription_items_prescription_id",
        table_name="prescription_items",
    )
    op.drop_table("prescription_items")