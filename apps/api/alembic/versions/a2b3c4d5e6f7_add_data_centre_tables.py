"""add_data_centre_tables

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-27 00:00:00.000000

MH-01: Data Centre Foundation
Creates four new tables for tracking market data imports, quality, gaps,
and provider coverage. Does NOT modify or duplicate the existing bars table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── market_data_import_runs ────────────────────────────────────────────
    op.create_table(
        'market_data_import_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('asset_symbol', sa.String(50), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('from_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('to_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rows_requested', sa.Integer(), nullable=True),
        sa.Column('rows_upserted', sa.Integer(), nullable=True),
        sa.Column('rows_skipped', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Numeric(10, 3), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_market_data_import_runs_provider', 'market_data_import_runs', ['provider'])
    op.create_index('ix_market_data_import_runs_asset_symbol', 'market_data_import_runs', ['asset_symbol'])

    # ── market_data_quality_reports ────────────────────────────────────────
    op.create_table(
        'market_data_quality_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('asset_symbol', sa.String(50), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('provider', sa.String(100), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_bars', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completeness_pct', sa.Float(), nullable=True),
        sa.Column('missing_bars', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicate_bars', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stale_bars', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('earliest_bar_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('latest_bar_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_market_data_quality_reports_asset_symbol', 'market_data_quality_reports', ['asset_symbol'])

    # ── market_data_gaps ───────────────────────────────────────────────────
    op.create_table(
        'market_data_gaps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('asset_symbol', sa.String(50), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('provider', sa.String(100), nullable=True),
        sa.Column('gap_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('gap_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='open'),
        sa.Column('import_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_market_data_gaps_asset_symbol', 'market_data_gaps', ['asset_symbol'])

    # ── provider_coverage_reports ──────────────────────────────────────────
    op.create_table(
        'provider_coverage_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_assets', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('covered_assets', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('coverage_pct', sa.Float(), nullable=True),
        sa.Column('earliest_bar_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('latest_bar_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_bars', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_provider_coverage_reports_provider', 'provider_coverage_reports', ['provider'])


def downgrade() -> None:
    op.drop_index('ix_provider_coverage_reports_provider', table_name='provider_coverage_reports')
    op.drop_table('provider_coverage_reports')

    op.drop_index('ix_market_data_gaps_asset_symbol', table_name='market_data_gaps')
    op.drop_table('market_data_gaps')

    op.drop_index('ix_market_data_quality_reports_asset_symbol', table_name='market_data_quality_reports')
    op.drop_table('market_data_quality_reports')

    op.drop_index('ix_market_data_import_runs_asset_symbol', table_name='market_data_import_runs')
    op.drop_index('ix_market_data_import_runs_provider', table_name='market_data_import_runs')
    op.drop_table('market_data_import_runs')
