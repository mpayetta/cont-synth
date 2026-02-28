"""add_llm_usage_log

Revision ID: c3f8a1d2e9b7
Revises: bf7d224a95e5
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'c3f8a1d2e9b7'
down_revision: Union[str, Sequence[str], None] = 'bf7d224a95e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'llmusagelog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('operation', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('interview_id', sa.Integer(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('output_tokens', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['interview_id'], ['interview.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('llmusagelog')
