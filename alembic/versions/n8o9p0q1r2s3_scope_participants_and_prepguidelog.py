"""add product_id to participant and prepguidelog for workspace scoping

Participants and PrepGuideLog were previously global (no product isolation).
This migration adds nullable product_id to both and backfills via existing
interview links (for participants) and the single product owned by user 1 (for prep logs).

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-03-07 10:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'n8o9p0q1r2s3'
down_revision: Union[str, None] = 'm7n8o9p0q1r2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Participant ───────────────────────────────────────────────────────────
    op.add_column('participant', sa.Column('product_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_participant_product_id', 'participant', 'product', ['product_id'], ['id']
    )

    # Backfill participant.product_id via InterviewParticipantLink → Interview.product_id
    # Each participant gets the product_id of the first interview they're linked to.
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE participant
        SET product_id = (
            SELECT i.product_id
            FROM interviewparticipantlink ipl
            JOIN interview i ON i.id = ipl.interview_id
            WHERE ipl.participant_id = participant.id
              AND i.product_id IS NOT NULL
            ORDER BY i.id
            LIMIT 1
        )
        WHERE product_id IS NULL
    """))

    # ── PrepGuideLog ──────────────────────────────────────────────────────────
    op.add_column('prepguidelog', sa.Column('product_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_prepguidelog_product_id', 'prepguidelog', 'product', ['product_id'], ['id']
    )

    # Backfill to the first/only product (id=1 for legacy single-product installs)
    first_product = conn.execute(
        sa.text("SELECT id FROM product ORDER BY id LIMIT 1")
    ).fetchone()
    if first_product:
        conn.execute(
            sa.text("UPDATE prepguidelog SET product_id = :pid WHERE product_id IS NULL"),
            {"pid": first_product[0]},
        )


def downgrade() -> None:
    op.drop_constraint('fk_prepguidelog_product_id', 'prepguidelog', type_='foreignkey')
    op.drop_column('prepguidelog', 'product_id')

    op.drop_constraint('fk_participant_product_id', 'participant', type_='foreignkey')
    op.drop_column('participant', 'product_id')
