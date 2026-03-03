"""add_experiment_description_and_success_metric

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-03-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    cols = {c['name'] for c in inspect(conn).get_columns('experiment')}
    if 'description' not in cols:
        op.add_column(
            'experiment',
            sa.Column('description', sa.String(), nullable=False, server_default=''),
        )
    if 'success_metric' not in cols:
        op.add_column(
            'experiment',
            sa.Column('success_metric', sa.String(), nullable=False, server_default=''),
        )


def downgrade() -> None:
    op.drop_column('experiment', 'success_metric')
    op.drop_column('experiment', 'description')
