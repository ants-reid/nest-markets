"""MH-148-A — Add ``broker_submit_decisions`` audit table.

Pure additive migration. Creates a new ``broker_submit_decisions`` table to
durably record the preflight decision computed before any broker submit
attempt. **No code path writes to this table in this migration.** A future
suffix (MH-148-C, paired with MH-147 unified ``would_block`` enforcement
semantics) will wire writes from the broker submit path.

Drift-lock guarantee:
* Adds a new table only — does not modify any existing table.
* Does not change worker behaviour, broker submit semantics, or any gate.
* Auto-paper enforcement, auto trading, and live trading remain OFF.
* ``assert_auto_trading_allowed()`` is unchanged and still blocks auto intent.

The table shape mirrors the existing ``risk_decisions`` audit pattern so the
follow-up writer can persist a structured snapshot of what the broker submit
preflight observed.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "x8y9z0a1b2c3"
down_revision = "v7w8x9y0z1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broker_submit_decisions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "signal_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "intent",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "would_block",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "blocked_reason_code",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "blocked_reason_text",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "preflight_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_broker_submit_decisions_created_at",
        "broker_submit_decisions",
        ["created_at"],
    )
    op.create_index(
        "ix_broker_submit_decisions_signal_id",
        "broker_submit_decisions",
        ["signal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_broker_submit_decisions_signal_id",
        table_name="broker_submit_decisions",
    )
    op.drop_index(
        "ix_broker_submit_decisions_created_at",
        table_name="broker_submit_decisions",
    )
    op.drop_table("broker_submit_decisions")
