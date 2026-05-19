"""Add signal_outcomes table for BP3-05 result capture.

Revision ID: e7f8g9h0i1j2
Revises: d058936fdd0d
Create Date: 2026-04-25 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e7f8g9h0i1j2"
down_revision = "d058936fdd0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create signal_outcomes table for AI learning loop outcome tracking."""
    op.create_table(
        "signal_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("setup_type", sa.String(100), nullable=False),
        sa.Column("direction", sa.String(50), nullable=False),
        sa.Column("horizon_label", sa.String(50), nullable=True),
        sa.Column("catalyst_type", sa.String(100), nullable=True),
        sa.Column("regime_at_entry", sa.String(100), nullable=True),
        sa.Column("entry_price", sa.Numeric(precision=16, scale=8), nullable=False),
        sa.Column("exit_price", sa.Numeric(precision=16, scale=8), nullable=False),
        sa.Column(
            "predicted_direction_correct",
            sa.Boolean(),
            nullable=True,
            comment="True if exit price moved in direction of signal; False if opposite or flat",
        ),
        sa.Column(
            "actual_pnl_pct",
            sa.Numeric(precision=10, scale=6),
            nullable=True,
            comment="Realized PnL as percentage of entry price",
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], name="fk_signal_outcomes_signal_id"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], name="fk_signal_outcomes_asset_id"),
        sa.PrimaryKeyConstraint("id", name="pk_signal_outcomes"),
    )


def downgrade() -> None:
    """Drop signal_outcomes table."""
    op.drop_table("signal_outcomes")
