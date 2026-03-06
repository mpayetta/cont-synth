"""add multi-user support: user role and product user_id

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-03-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'i3j4k5l6m7n8'
down_revision: Union[str, None] = 'h2i3j4k5l6m7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add role column to user table (default 'user' for all existing rows)
    op.add_column('user', sa.Column('role', sa.Text(), nullable=False, server_default='user'))
    # Promote the first/lowest-ID user to role='admin'
    op.execute("UPDATE \"user\" SET role = 'admin' WHERE id = (SELECT MIN(id) FROM \"user\")")

    # 2. Add user_id FK to product table
    op.add_column('product', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_product_user_id', 'product', 'user', ['user_id'], ['id']
    )
    # Backfill: assign all existing products to the first/lowest-ID user
    op.execute(
        "UPDATE product SET user_id = (SELECT id FROM \"user\" ORDER BY id LIMIT 1)"
    )


def downgrade() -> None:
    op.drop_constraint('fk_product_user_id', 'product', type_='foreignkey')
    op.drop_column('product', 'user_id')
    op.drop_column('user', 'role')
