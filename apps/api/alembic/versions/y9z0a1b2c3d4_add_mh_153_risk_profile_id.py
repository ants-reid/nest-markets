"""MH-153-A — Additive nullable ``risk_profile_id`` column on ``risk_decisions``.

Pure additive migration. Adds a nullable ``risk_profile_id UUID`` column to
``risk_decisions`` so a future writer (MH-153-B, paired with the MH-148-C
broker-submit-decision writer) can persist a denormalised snapshot of the
risk profile id observed at submit time.

**No production writer is wired in this migration.** No existing column is
modified. No FK constraint is added — the column is a denorm snapshot, kept
deliberately uncoupled from `risk_profiles.id` so the writer path can record
historical values even after a profile is deleted/replaced.

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
from sqlalchemy.dialects import postgresql

revision = "y9z0a1b2c3d4"
down_revision = "x8y9z0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "risk_decisions",
        sa.Column(
            "risk_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_risk_decisions_risk_profile_id",
        "risk_decisions",
        ["risk_profile_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_risk_decisions_risk_profile_id",
        table_name="risk_decisions",
    )
    op.drop_column("risk_decisions", "risk_profile_id")
