"""Add OTP codes table and lockout fields

Revision ID: 20260217_0001
Revises:
Create Date: 2026-02-17 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260217_0001"
down_revision = "20260217_0000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('create extension if not exists "uuid-ossp"')
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "otp_codes" not in tables:
        op.create_table(
            "otp_codes",
            sa.Column(
                "otp_id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("uuid_generate_v4()"),
                nullable=False,
            ),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("phone", sa.String(length=20), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("code_hash", sa.String(length=255), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("failed_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("lock_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
            sa.PrimaryKeyConstraint("otp_id"),
        )
        op.create_index(
            "ix_otp_lookup",
            "otp_codes",
            ["phone", "role", "tenant_id", "used"],
            unique=False,
        )
        return

    columns = {col["name"] for col in inspector.get_columns("otp_codes")}
    if "failed_attempts" not in columns:
        op.add_column(
            "otp_codes",
            sa.Column("failed_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        )
    if "lock_until" not in columns:
        op.add_column("otp_codes", sa.Column("lock_until", sa.DateTime(timezone=True), nullable=True))

    indexes = {idx["name"] for idx in inspector.get_indexes("otp_codes")}
    if "ix_otp_lookup" not in indexes:
        op.create_index(
            "ix_otp_lookup",
            "otp_codes",
            ["phone", "role", "tenant_id", "used"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    if "otp_codes" not in tables:
        return

    indexes = {idx["name"] for idx in inspector.get_indexes("otp_codes")}
    if "ix_otp_lookup" in indexes:
        op.drop_index("ix_otp_lookup", table_name="otp_codes")

    columns = {col["name"] for col in inspector.get_columns("otp_codes")}
    if "lock_until" in columns:
        op.drop_column("otp_codes", "lock_until")
    if "failed_attempts" in columns:
        op.drop_column("otp_codes", "failed_attempts")

    # Table drop is intentionally omitted to avoid deleting pre-existing OTP data.
