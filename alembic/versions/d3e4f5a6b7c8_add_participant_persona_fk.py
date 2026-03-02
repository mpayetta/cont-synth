"""add_participant_persona_fk

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-03-01 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable persona_id FK column to participant table."""
    conn = op.get_bind()
    cols = {c['name'] for c in inspect(conn).get_columns('participant')}
    if 'persona_id' not in cols:
        op.add_column(
            'participant',
            sa.Column('persona_id', sa.Integer(), nullable=True),
        )
        # SQLite doesn't enforce FKs by default, but we still declare it for clarity
        # (adding a FK constraint to an existing table requires batch mode in SQLite)
        with op.batch_alter_table('participant') as batch_op:
            batch_op.create_foreign_key(
                'fk_participant_persona_id',
                'persona',
                ['persona_id'],
                ['id'],
            )


def downgrade() -> None:
    """Remove persona_id column from participant table."""
    with op.batch_alter_table('participant') as batch_op:
        batch_op.drop_constraint('fk_participant_persona_id', type_='foreignkey')
        batch_op.drop_column('persona_id')
