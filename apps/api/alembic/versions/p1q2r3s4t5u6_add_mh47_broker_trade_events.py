"""MH-47B — Add broker_trade_events table for normalized trade/fill staging."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "p1q2r3s4t5u6"
down_revision = "o0p1q2r3s4t5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broker_trade_events",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("broker_provider", sa.String(length=50), nullable=False, server_default="ibkr"),
        sa.Column("account_id", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="broker_account_trades"),
        sa.Column("event_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("external_trade_id", sa.String(length=128), nullable=True),
        sa.Column("broker_order_id", sa.String(length=128), nullable=True),
        sa.Column("symbol", sa.String(length=64), nullable=True),
        sa.Column("side", sa.String(length=16), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=True),
        sa.Column("fill_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("commission", sa.Numeric(18, 8), nullable=True),
        sa.Column("net_amount", sa.Numeric(18, 8), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(18, 8), nullable=True),
        sa.Column("trade_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("event_fingerprint", name="uq_broker_trade_event_fingerprint"),
    )

    op.create_index("ix_broker_trade_events_event_fingerprint", "broker_trade_events", ["event_fingerprint"])
    op.create_index("ix_broker_trade_events_account_id", "broker_trade_events", ["account_id"])
    op.create_index("ix_broker_trade_events_broker_order_id", "broker_trade_events", ["broker_order_id"])
    op.create_index("ix_broker_trade_events_symbol", "broker_trade_events", ["symbol"])
    op.create_index("ix_broker_trade_events_trade_ts", "broker_trade_events", ["trade_ts"])


def downgrade() -> None:
    op.drop_index("ix_broker_trade_events_trade_ts", table_name="broker_trade_events")
    op.drop_index("ix_broker_trade_events_symbol", table_name="broker_trade_events")
    op.drop_index("ix_broker_trade_events_broker_order_id", table_name="broker_trade_events")
    op.drop_index("ix_broker_trade_events_account_id", table_name="broker_trade_events")
    op.drop_index("ix_broker_trade_events_event_fingerprint", table_name="broker_trade_events")
    op.drop_table("broker_trade_events")
