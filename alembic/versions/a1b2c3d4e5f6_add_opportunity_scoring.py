"""add_opportunity_scoring

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-03-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f2e9a0947ef7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Torres prioritization scores and target designation to opportunity."""
    conn = op.get_bind()
    existing_cols = {col['name'] for col in inspect(conn).get_columns('opportunity')}

    if 'impact_score' not in existing_cols:
        op.add_column('opportunity', sa.Column('impact_score', sa.Integer(), nullable=False, server_default='0'))

    if 'sat_gap_score' not in existing_cols:
        op.add_column('opportunity', sa.Column('sat_gap_score', sa.Integer(), nullable=False, server_default='0'))

    if 'is_target' not in existing_cols:
        op.add_column('opportunity', sa.Column('is_target', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Remove scoring columns from opportunity."""
    op.drop_column('opportunity', 'is_target')
    op.drop_column('opportunity', 'sat_gap_score')
    op.drop_column('opportunity', 'impact_score')
