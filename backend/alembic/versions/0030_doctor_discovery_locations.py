"""Add doctor specialties and private facility coordinates.

Revision ID: 0030_doctor_locations
Revises: 0029_access_grant_scopes
"""

from alembic import op
import sqlalchemy as sa


revision = "0030_doctor_locations"
down_revision = "0029_access_grant_scopes"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("healthcare_facilities") as batch:
        batch.add_column(sa.Column("district_code", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("upazila_code", sa.String(length=20), nullable=True))
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch.add_column(
            sa.Column(
                "location_status",
                sa.String(length=24),
                nullable=False,
                server_default="PENDING",
            )
        )
        batch.add_column(sa.Column("location_matched_address", sa.Text(), nullable=True))
        batch.add_column(sa.Column("location_confirmed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_check_constraint(
            op.f("ck_healthcare_facilities_valid_location_status"),
            "location_status IN ('PENDING', 'CONFIRMED')",
        )
        batch.create_check_constraint(
            op.f("ck_healthcare_facilities_valid_latitude"),
            "latitude IS NULL OR (latitude BETWEEN 20 AND 27)",
        )
        batch.create_check_constraint(
            op.f("ck_healthcare_facilities_valid_longitude"),
            "longitude IS NULL OR (longitude BETWEEN 88 AND 93)",
        )
        batch.create_index(
            "ix_healthcare_facilities_area",
            ["district_code", "upazila_code", "location_status"],
        )

    with op.batch_alter_table("doctor_registration_details") as batch:
        batch.add_column(
            sa.Column(
                "specialization",
                sa.String(length=64),
                nullable=False,
                server_default="GENERAL_MEDICINE",
            )
        )
        batch.add_column(sa.Column("qualification", sa.String(length=255), nullable=True))
        batch.create_index(
            "ix_doctor_registration_details_specialization", ["specialization"]
        )


def downgrade():
    with op.batch_alter_table("doctor_registration_details") as batch:
        batch.drop_index("ix_doctor_registration_details_specialization")
        batch.drop_column("qualification")
        batch.drop_column("specialization")

    with op.batch_alter_table("healthcare_facilities") as batch:
        batch.drop_index("ix_healthcare_facilities_area")
        batch.drop_constraint(
            op.f("ck_healthcare_facilities_valid_longitude"), type_="check"
        )
        batch.drop_constraint(
            op.f("ck_healthcare_facilities_valid_latitude"), type_="check"
        )
        batch.drop_constraint(
            op.f("ck_healthcare_facilities_valid_location_status"), type_="check"
        )
        batch.drop_column("location_confirmed_at")
        batch.drop_column("location_matched_address")
        batch.drop_column("location_status")
        batch.drop_column("longitude")
        batch.drop_column("latitude")
        batch.drop_column("upazila_code")
        batch.drop_column("district_code")
