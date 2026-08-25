"""update Conversation

Revision ID: aae5ca8edd94
Revises: d613cbe57a1d
Create Date: 2026-08-05 18:14:07.759934

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aae5ca8edd94'
down_revision: Union[str, Sequence[str], None] = 'd613cbe57a1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Normalize conversation table: title NOT NULL, created_at with timezone.
    op.alter_column(
        'conversations',
        'title',
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        'conversations',
        'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'conversations',
        'created_at',
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        'conversations',
        'title',
        existing_type=sa.String(length=255),
        nullable=False,
    )
