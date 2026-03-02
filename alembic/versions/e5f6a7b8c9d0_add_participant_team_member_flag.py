"""add_participant_team_member_flag

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
Create Date: 2026-03-01 00:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_team_member boolean column to participant table."""
    conn = op.get_bind()
    cols = {c['name'] for c in inspect(conn).get_columns('participant')}
    if 'is_team_member' not in cols:
        op.add_column(
            'participant',
            sa.Column('is_team_member', sa.Boolean(), nullable=False, server_default='0'),
        )


def downgrade() -> None:
    """Remove is_team_member column from participant table."""
    op.drop_column('participant', 'is_team_member')
