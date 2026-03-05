"""add knowledge base (drop knowledgechunk, add workspacedocument + documentchunk)

Revision ID: g1h2i3j4k5l6
Revises: f3a4b5c6d7e8
Create Date: 2026-03-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector extension is available
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Drop the old KnowledgeChunk table
    op.drop_table('knowledgechunk')

    # Create WorkspaceDocument table
    op.create_table(
        'workspacedocument',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('filename', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('upload_date', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['product.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create DocumentChunk table — use raw SQL for the vector column because
    # SQLAlchemy's generic DDL doesn't know about pgvector natively.
    op.execute("""
        CREATE TABLE documentchunk (
            id SERIAL PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES workspacedocument(id),
            chunk_text TEXT NOT NULL,
            embedding vector(384)
        )
    """)


def downgrade() -> None:
    op.drop_table('documentchunk')
    op.drop_table('workspacedocument')

    # Recreate the original KnowledgeChunk table
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute("""
        CREATE TABLE knowledgechunk (
            id SERIAL PRIMARY KEY,
            workspace_id INTEGER NOT NULL,
            document_name TEXT NOT NULL,
            text_content TEXT NOT NULL,
            embedding vector(384)
        )
    """)
