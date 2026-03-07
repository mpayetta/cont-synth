"""add productmember workspace membership table

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-03-07 10:00:00.000000
"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'k5l6m7n8o9p0'
down_revision: Union[str, None] = 'j4k5l6m7n8o9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'productmember',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='member'),
        sa.Column('invited_by_user_id', sa.Integer(), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['product.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['invited_by_user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'user_id', name='uq_productmember_product_user'),
    )
    op.create_index('ix_productmember_product_id', 'productmember', ['product_id'])
    op.create_index('ix_productmember_user_id', 'productmember', ['user_id'])

    # Backfill: for each existing Product, create an "admin" ProductMember row for its owner
    conn = op.get_bind()
    products = conn.execute(
        sa.text("SELECT id, user_id, created_at FROM product WHERE user_id IS NOT NULL")
    ).fetchall()
    now = datetime.now(timezone.utc)
    for prod_id, user_id, created_at in products:
        joined = created_at if created_at else now
        conn.execute(
            sa.text(
                "INSERT INTO productmember (product_id, user_id, role, invited_by_user_id, joined_at) "
                "VALUES (:pid, :uid, 'admin', NULL, :jat) "
                "ON CONFLICT (product_id, user_id) DO NOTHING"
            ),
            {"pid": prod_id, "uid": user_id, "jat": joined},
        )


def downgrade() -> None:
    op.drop_index('ix_productmember_user_id', table_name='productmember')
    op.drop_index('ix_productmember_product_id', table_name='productmember')
    op.drop_table('productmember')
