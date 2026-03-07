"""add created_by/updated_by/updated_at audit fields to mutable models

Adds inline authorship tracking to Interview, Opportunity, Outcome, Solution, Experiment.
All existing rows are backfilled with user_id = 1 (the original admin).

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-03-07 10:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'l6m7n8o9p0q1'
down_revision: Union[str, None] = 'k5l6m7n8o9p0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_AUDIT_TABLES = ['interview', 'opportunity', 'outcome', 'solution', 'experiment']


def upgrade() -> None:
    for table in _AUDIT_TABLES:
        op.add_column(table, sa.Column('created_by_user_id', sa.Integer(), nullable=True))
        op.add_column(table, sa.Column('updated_by_user_id', sa.Integer(), nullable=True))
        op.add_column(table, sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        op.create_foreign_key(
            f'fk_{table}_created_by_user_id',
            table, 'user', ['created_by_user_id'], ['id'],
        )
        op.create_foreign_key(
            f'fk_{table}_updated_by_user_id',
            table, 'user', ['updated_by_user_id'], ['id'],
        )

    # Backfill: assign admin user (id=1) as creator for all existing rows
    conn = op.get_bind()
    admin = conn.execute(
        sa.text('SELECT id FROM "user" ORDER BY id LIMIT 1')
    ).fetchone()
    if admin:
        admin_id = admin[0]
        for table in _AUDIT_TABLES:
            conn.execute(
                sa.text(f'UPDATE {table} SET created_by_user_id = :uid WHERE created_by_user_id IS NULL'),
                {"uid": admin_id},
            )


def downgrade() -> None:
    for table in _AUDIT_TABLES:
        op.drop_constraint(f'fk_{table}_updated_by_user_id', table, type_='foreignkey')
        op.drop_constraint(f'fk_{table}_created_by_user_id', table, type_='foreignkey')
        op.drop_column(table, 'updated_at')
        op.drop_column(table, 'updated_by_user_id')
        op.drop_column(table, 'created_by_user_id')
