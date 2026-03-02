"""add_interview_metadata

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-02-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add optional metadata columns to the interview table."""
    conn = op.get_bind()
    existing_cols = {col['name'] for col in inspect(conn).get_columns('interview')}

    if 'duration_minutes' not in existing_cols:
        op.add_column('interview', sa.Column('duration_minutes', sa.Integer(), nullable=True))

    if 'interview_date' not in existing_cols:
        op.add_column('interview', sa.Column('interview_date', sa.String(), nullable=True))

    if 'participants' not in existing_cols:
        op.add_column('interview', sa.Column('participants', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove metadata columns from the interview table."""
    op.drop_column('interview', 'participants')
    op.drop_column('interview', 'interview_date')
    op.drop_column('interview', 'duration_minutes')
