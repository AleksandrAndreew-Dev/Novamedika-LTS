"""fix duplicate refresh token constraint

Remove unique constraint from refresh_tokens.token column to prevent
IntegrityError when multiple concurrent requests try to create tokens.

Revision ID: fix_duplicate_refresh_token
Revises: 3b81fefeff37
Create Date: 2026-04-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_duplicate_refresh_token'
down_revision: Union[str, None] = '3b81fefeff37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the unique constraint on token column
    op.drop_index('ix_refresh_tokens_token', table_name='refresh_tokens')
    # Recreate as non-unique index for performance
    op.create_index('ix_refresh_tokens_token', 'refresh_tokens', ['token'])


def downgrade() -> None:
    # Restore the unique constraint
    op.drop_index('ix_refresh_tokens_token', table_name='refresh_tokens')
    op.create_index('ix_refresh_tokens_token', 'refresh_tokens', ['token'], unique=True)