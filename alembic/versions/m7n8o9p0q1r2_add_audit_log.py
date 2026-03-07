"""add auditlog table for immutable event trail

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2026-03-07 10:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'm7n8o9p0q1r2'
down_revision: Union[str, None] = 'l6m7n8o9p0q1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auditlog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('detail', sa.String(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['product_id'], ['product.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auditlog_user_id', 'auditlog', ['user_id'])
    op.create_index('ix_auditlog_product_id', 'auditlog', ['product_id'])


def downgrade() -> None:
    op.drop_index('ix_auditlog_product_id', table_name='auditlog')
    op.drop_index('ix_auditlog_user_id', table_name='auditlog')
    op.drop_table('auditlog')
