"""create prescription documents

Revision ID: 0023_prescription_documents
Revises: 0022_prescription_items
Create Date: 2026-08-21

Adds the prescription PDF pointer table from V6 section 28. Each
prescription has at most one current PDF document (``UNIQUE`` on
``prescription_id``); the PDF binary itself lives in private storage
(local filesystem in development, object storage in production) under
``storage_key``. The PDF is regenerated on every prescription edit by
the author doctor and the document row is updated in place.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0023_prescription_documents"
down_revision: str | None = "0022_prescription_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prescription_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "prescription_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "storage_key", sa.String(length=500), nullable=False
        ),
        sa.Column(
            "file_name", sa.String(length=255), nullable=False
        ),
        sa.Column(
            "content_type",
            sa.String(length=100),
            nullable=False,
            server_default="application/pdf",
        ),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "generated_at",
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
            ["prescription_id"],
            ["prescriptions.id"],
            name=op.f(
                "fk_prescription_documents_prescription_id_prescriptions"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_prescription_documents")
        ),
        sa.UniqueConstraint(
            "prescription_id",
            name=op.f("uq_prescription_documents_prescription_id"),
        ),
    )
    op.create_index(
        "ix_prescription_documents_prescription_id",
        "prescription_documents",
        ["prescription_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prescription_documents_prescription_id",
        table_name="prescription_documents",
    )
    op.drop_table("prescription_documents")