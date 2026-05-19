"""add_mh03_quality_fields

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-04-27 00:00:00.000000

MH-03: Data Quality Engine
- Extends market_data_quality_reports with deterministic quality metrics
- Extends market_data_gaps with expected missing candles and severity
"""

from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "market_data_quality_reports",
        sa.Column("expected_bars", sa.Integer(), nullable=True),
    )
    op.add_column(
        "market_data_quality_reports",
        sa.Column("actual_bars", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "market_data_quality_reports",
        sa.Column("bad_price_bars", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "market_data_quality_reports",
        sa.Column("suspicious_spike_bars", sa.Integer(), nullable=False, server_default="0"),
    )

    op.add_column(
        "market_data_gaps",
        sa.Column("expected_candles_missing", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "market_data_gaps",
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="low"),
    )


def downgrade() -> None:
    op.drop_column("market_data_gaps", "severity")
    op.drop_column("market_data_gaps", "expected_candles_missing")

    op.drop_column("market_data_quality_reports", "suspicious_spike_bars")
    op.drop_column("market_data_quality_reports", "bad_price_bars")
    op.drop_column("market_data_quality_reports", "actual_bars")
    op.drop_column("market_data_quality_reports", "expected_bars")
