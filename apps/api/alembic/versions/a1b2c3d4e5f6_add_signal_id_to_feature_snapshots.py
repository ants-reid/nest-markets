"""add_signal_id_to_feature_snapshots

Revision ID: a1b2c3d4e5f6
Revises: d058936fdd0d
Create Date: 2026-04-24 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a1b2c3d4e5f6'
down_revision = 'd058936fdd0d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'feature_snapshots',
        sa.Column(
            'signal_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('signals.id'),
            nullable=True,
        ),
    )
    op.create_index(
        'ix_feature_snapshots_signal_id',
        'feature_snapshots',
        ['signal_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_feature_snapshots_signal_id', table_name='feature_snapshots')
    op.drop_column('feature_snapshots', 'signal_id')
