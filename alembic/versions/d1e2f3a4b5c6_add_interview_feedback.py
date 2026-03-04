"""add interview feedback

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-03-04 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'interviewfeedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('interview_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('keep_doing', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('stop_doing', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('start_doing', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('trend_analysis', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['interview_id'], ['interview.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('interview_id'),
    )
    op.create_index('ix_interviewfeedback_interview_id', 'interviewfeedback', ['interview_id'])


def downgrade() -> None:
    op.drop_index('ix_interviewfeedback_interview_id', 'interviewfeedback')
    op.drop_table('interviewfeedback')
