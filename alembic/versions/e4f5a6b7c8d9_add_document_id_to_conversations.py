"""add document_id to conversations

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-08-28 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'conversations',
        sa.Column('document_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_conversations_document_id',
        'conversations',
        'documents',
        ['document_id'],
        ['id'],
    )
    op.create_index(
        'ix_conversations_document_id',
        'conversations',
        ['document_id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_conversations_document_id', table_name='conversations')
    op.drop_constraint('fk_conversations_document_id', 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'document_id')
