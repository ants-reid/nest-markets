"""add_mh02_import_batch_and_coverage

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-04-27 00:00:00.000000

MH-02: Historical Import Manager
- Adds batch_id to market_data_import_runs (groups per-asset runs into one request)
- Adds quality_score + approved_for_backtest columns to market_data_quality_reports
- Creates provider_asset_coverage table (granular per provider+asset+timeframe coverage)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── market_data_import_runs: add batch_id ─────────────────────────────
    op.add_column(
        'market_data_import_runs',
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        'ix_market_data_import_runs_batch_id',
        'market_data_import_runs',
        ['batch_id'],
    )

    # ── market_data_quality_reports: add quality_score + approved_for_backtest
    op.add_column(
        'market_data_quality_reports',
        sa.Column('quality_score', sa.Float(), nullable=True),
    )
    op.add_column(
        'market_data_quality_reports',
        sa.Column('approved_for_backtest', sa.Boolean(), nullable=False, server_default='false'),
    )

    # ── provider_asset_coverage ────────────────────────────────────────────
    op.create_table(
        'provider_asset_coverage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('asset_symbol', sa.String(50), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('requested_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requested_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('available_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('available_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('candle_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('missing_pct', sa.Float(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('approved_for_backtest', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('limitations', sa.Text(), nullable=True),
        sa.Column('last_import_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('provider', 'asset_symbol', 'timeframe', name='uq_pac_provider_asset_tf'),
    )
    op.create_index('ix_provider_asset_coverage_provider', 'provider_asset_coverage', ['provider'])
    op.create_index('ix_provider_asset_coverage_asset_symbol', 'provider_asset_coverage', ['asset_symbol'])


def downgrade() -> None:
    op.drop_index('ix_provider_asset_coverage_asset_symbol', table_name='provider_asset_coverage')
    op.drop_index('ix_provider_asset_coverage_provider', table_name='provider_asset_coverage')
    op.drop_table('provider_asset_coverage')

    op.drop_column('market_data_quality_reports', 'approved_for_backtest')
    op.drop_column('market_data_quality_reports', 'quality_score')

    op.drop_index('ix_market_data_import_runs_batch_id', table_name='market_data_import_runs')
    op.drop_column('market_data_import_runs', 'batch_id')
