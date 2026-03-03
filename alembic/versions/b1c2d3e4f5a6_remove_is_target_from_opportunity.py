"""remove_is_target_from_opportunity

Revision ID: b1c2d3e4f5a6
Revises: a2b3c4d5e6f7
Create Date: 2026-03-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('opportunity', 'is_target')


def downgrade() -> None:
    op.add_column(
        'opportunity',
        sa.Column('is_target', sa.Boolean(), nullable=False, server_default='0'),
    )
