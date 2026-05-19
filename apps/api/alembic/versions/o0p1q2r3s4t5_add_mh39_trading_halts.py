"""MH-39 — Add trading_halts table for future emergency stop enforcement."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "o0p1q2r3s4t5"
down_revision = "n9o0p1q2r3s4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trading_halts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("halt_type", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("scope", sa.String(length=50), nullable=False, server_default="global"),
        sa.Column("trading_mode", sa.String(length=20), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.String(length=100), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_by", sa.String(length=100), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_trading_halts_status", "trading_halts", ["status"])
    op.create_index("ix_trading_halts_triggered_at", "trading_halts", ["triggered_at"])
    op.create_index("ix_trading_halts_scope_status", "trading_halts", ["scope", "status"])

    op.execute(
        sa.text(
            """
            INSERT INTO trading_halts (
                id, status, halt_type, scope, triggered_at, resolution_notes
            ) VALUES (
                :id, 'resolved', 'system', 'global', now(),
                'MH-39 foundation row created for migration verification only; halt enforcement remains disabled.'
            )
            """
        ).bindparams(id=uuid.uuid4())
    )


def downgrade() -> None:
    op.drop_index("ix_trading_halts_scope_status", table_name="trading_halts")
    op.drop_index("ix_trading_halts_triggered_at", table_name="trading_halts")
    op.drop_index("ix_trading_halts_status", table_name="trading_halts")
    op.drop_table("trading_halts")