"""MH-146 — Add Position.opened_by attribution column.

Distinguishes how a position was opened (auto_paper / manual_paper / live / unknown)
so capacity counts and per-mode performance attribution stop conflating
``close_reason='auto_paper'`` (a close-time tag) with open-time origin.

Pure additive column with safe default ('unknown'). No production query
currently reads this column; future phases (MH-155 SignalOutcome attribution,
MH-MON-04 trading-safety aggregator) will adopt it.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "s4t5u6v7w8x9"
down_revision = "r3s4t5u6v7w8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "positions",
        sa.Column(
            "opened_by",
            sa.String(length=20),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.create_check_constraint(
        "ck_positions_opened_by",
        "positions",
        "opened_by IN ('auto_paper', 'manual_paper', 'live', 'unknown')",
    )
    op.create_index(
        "ix_positions_opened_by_status",
        "positions",
        ["opened_by", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_positions_opened_by_status", table_name="positions")
    op.drop_constraint("ck_positions_opened_by", "positions", type_="check")
    op.drop_column("positions", "opened_by")
