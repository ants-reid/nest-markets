"""MH-38 — Add risk_limit_configs table for future enforcement foundation."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "n9o0p1q2r3s4"
down_revision = "m8n9o0p1q2r3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "risk_limit_configs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope", sa.String(length=50), nullable=False, server_default="global"),
        sa.Column("trading_mode", sa.String(length=20), nullable=False, server_default="paper"),
        sa.Column("max_order_notional", sa.Numeric(18, 8), nullable=True),
        sa.Column("daily_loss_limit_amount", sa.Numeric(18, 8), nullable=True),
        sa.Column("daily_loss_limit_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_open_positions", sa.Integer(), nullable=True),
        sa.Column("max_total_exposure", sa.Numeric(18, 8), nullable=True),
        sa.Column("max_symbol_exposure", sa.Numeric(18, 8), nullable=True),
        sa.Column("max_trades_per_day", sa.Integer(), nullable=True),
        sa.Column("min_cash_buffer", sa.Numeric(18, 8), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_risk_limit_configs_scope", "risk_limit_configs", ["scope"])
    op.create_index("ix_risk_limit_configs_mode_active", "risk_limit_configs", ["trading_mode", "is_active"])

    op.execute(
        sa.text(
            """
            INSERT INTO risk_limit_configs (
                id, scope, trading_mode, is_active, notes
            ) VALUES (
                :id, 'global', 'paper', true,
                'MH-38 default risk-limit foundation row; limits intentionally not enforced yet.'
            )
            """
        ).bindparams(id=uuid.uuid4())
    )


def downgrade() -> None:
    op.drop_index("ix_risk_limit_configs_mode_active", table_name="risk_limit_configs")
    op.drop_index("ix_risk_limit_configs_scope", table_name="risk_limit_configs")
    op.drop_table("risk_limit_configs")