"""add_broker_fields_phase_15

Revision ID: f1a2b3c4d5e6
Revises: d058936fdd0d
Create Date: 2026-04-25 09:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'f1a2b3c4d5e6'
down_revision = 'd058936fdd0d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add broker-specific fields for IBKR integration (Phase 15)."""
    # Add ibkr_con_id to assets table
    op.add_column('assets', sa.Column('ibkr_con_id', sa.Integer(), nullable=True))
    
    # Add broker fields to paper_orders
    op.add_column('paper_orders', sa.Column('broker_order_id', sa.String(length=255), nullable=True))
    op.add_column('paper_orders', sa.Column('commission', sa.Numeric(precision=18, scale=8), nullable=True))
    op.add_column('paper_orders', sa.Column('avg_fill_price', sa.Numeric(precision=18, scale=8), nullable=True))
    op.add_column('paper_orders', sa.Column('ibkr_status', sa.String(length=50), nullable=True))
    
    # Add broker fields to positions table (if it exists)
    try:
        op.add_column('positions', sa.Column('broker_order_id', sa.String(length=255), nullable=True))
        op.add_column('positions', sa.Column('ibkr_con_id', sa.Integer(), nullable=True))
        op.add_column('positions', sa.Column('market_value', sa.Numeric(precision=18, scale=8), nullable=True))
        op.add_column('positions', sa.Column('commission_paid', sa.Numeric(precision=18, scale=8), nullable=True))
    except Exception:
        pass  # positions table may not exist yet


def downgrade() -> None:
    """Rollback broker fields."""
    try:
        op.drop_column('positions', 'commission_paid')
        op.drop_column('positions', 'market_value')
        op.drop_column('positions', 'ibkr_con_id')
        op.drop_column('positions', 'broker_order_id')
    except Exception:
        pass
    
    op.drop_column('paper_orders', 'ibkr_status')
    op.drop_column('paper_orders', 'avg_fill_price')
    op.drop_column('paper_orders', 'commission')
    op.drop_column('paper_orders', 'broker_order_id')
    op.drop_column('assets', 'ibkr_con_id')
