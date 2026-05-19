"""MH-154-A — Additive nullable ``block_reason_code`` column on ``risk_decisions``.

Pure additive migration. Adds a nullable ``block_reason_code VARCHAR(64)``
column to ``risk_decisions`` for the structured/queryable enum-as-string side
of the risk-block reason.

The free-text side already exists (``blocking_rule``); this column is its
queryable companion. **No production writer is wired in this migration.**
A future suffix (MH-154-B) populates it; existing writers continue to
populate ``blocking_rule`` and ``blocked_reasons_json`` exactly as today.

Drift-lock guarantee:
* Auto-paper enforcement remains OFF.
* Auto trading remains OFF.
* Live trading remains OFF.
* ``assert_auto_trading_allowed()`` is unchanged and still blocks auto intent.
* No worker, broker, or trading_control change.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "z0a1b2c3d4e5"
down_revision = "y9z0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "risk_decisions",
        sa.Column(
            "block_reason_code",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_risk_decisions_block_reason_code",
        "risk_decisions",
        ["block_reason_code"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_risk_decisions_block_reason_code",
        table_name="risk_decisions",
    )
    op.drop_column("risk_decisions", "block_reason_code")
