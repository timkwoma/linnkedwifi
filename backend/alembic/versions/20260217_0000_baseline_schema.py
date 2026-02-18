"""Baseline schema from ORM metadata

Revision ID: 20260217_0000
Revises:
Create Date: 2026-02-17 00:00:00
"""

from __future__ import annotations

from alembic import op

from linkedwifi_saas.database import Base
from linkedwifi_saas import models  # noqa: F401

# revision identifiers, used by Alembic.
revision = "20260217_0000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('create extension if not exists "uuid-ossp"')
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    # Baseline downgrade is intentionally non-destructive.
    pass
