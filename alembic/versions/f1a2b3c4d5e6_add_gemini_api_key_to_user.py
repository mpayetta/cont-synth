"""add_gemini_api_key_to_user

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-03-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add gemini_api_key nullable column to user table."""
    conn = op.get_bind()
    cols = {c['name'] for c in inspect(conn).get_columns('user')}
    if 'gemini_api_key' not in cols:
        op.add_column(
            'user',
            sa.Column('gemini_api_key', sa.String(), nullable=True),
        )


def downgrade() -> None:
    """Remove gemini_api_key column from user table."""
    op.drop_column('user', 'gemini_api_key')
