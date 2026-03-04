"""add prep guide log input fields

Revision ID: f3a4b5c6d7e8
Revises: 65cba31159d2
Create Date: 2026-03-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, None] = '65cba31159d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('prepguidelog', schema=None) as batch_op:
        batch_op.add_column(sa.Column('guide_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default='battle_plan'))
        batch_op.add_column(sa.Column('input_opportunities', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('input_extra_context', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('input_coach_score', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('input_stop_doing', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))


def downgrade() -> None:
    with op.batch_alter_table('prepguidelog', schema=None) as batch_op:
        batch_op.drop_column('input_stop_doing')
        batch_op.drop_column('input_coach_score')
        batch_op.drop_column('input_extra_context')
        batch_op.drop_column('input_opportunities')
        batch_op.drop_column('guide_type')
