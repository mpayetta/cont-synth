"""add_participant_crm

Revision ID: c2d3e4f5a6b7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create participant and interviewparticipantlink tables."""
    conn = op.get_bind()
    existing = inspect(conn).get_table_names()

    if 'participant' not in existing:
        op.create_table(
            'participant',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('segment', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('recruited_via', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_participant_name', 'participant', ['name'])

    if 'interviewparticipantlink' not in existing:
        op.create_table(
            'interviewparticipantlink',
            sa.Column('interview_id', sa.Integer(), nullable=False),
            sa.Column('participant_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['interview_id'], ['interview.id']),
            sa.ForeignKeyConstraint(['participant_id'], ['participant.id']),
            sa.PrimaryKeyConstraint('interview_id', 'participant_id'),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('interviewparticipantlink')
    op.drop_index('ix_participant_name', table_name='participant')
    op.drop_table('participant')
