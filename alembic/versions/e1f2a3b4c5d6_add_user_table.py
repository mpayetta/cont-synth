"""add_user_table

Revision ID: e1f2a3b4c5d6
Revises: c3f8a1d2e9b7
Create Date: 2026-02-28 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'c3f8a1d2e9b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create user table and seed default admin user."""
    conn = op.get_bind()

    # Only create the table if it doesn't already exist (idempotent).
    if 'user' not in inspect(conn).get_table_names():
        op.create_table(
            'user',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('username', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('password_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('fullname', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('username'),
        )

    # Only insert the default user if the table is empty.
    count = conn.execute(sa.text("SELECT COUNT(*) FROM user")).scalar()
    if count == 0:
        import bcrypt
        hashed = bcrypt.hashpw(b"admin1234!", bcrypt.gensalt()).decode("utf-8")
        conn.execute(
            sa.text(
                "INSERT INTO user (username, password_hash, fullname) "
                "VALUES (:username, :password_hash, :fullname)"
            ),
            {"username": "admin", "password_hash": hashed, "fullname": "Admin User"},
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('user')
