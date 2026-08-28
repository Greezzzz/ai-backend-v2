"""add user_id to conversations

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-08-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Kolom dibuat nullable dulu (baris lama tetap NULL = unowned), lalu FK + index.
    op.add_column(
        'conversations',
        sa.Column('user_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_conversations_user_id',
        'conversations',
        'users',
        ['user_id'],
        ['id'],
    )
    op.create_index(
        'ix_conversations_user_id',
        'conversations',
        ['user_id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_conversations_user_id', table_name='conversations')
    op.drop_constraint('fk_conversations_user_id', 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'user_id')
