"""add_consent_fields_to_users

Revision ID: 319072f585af
Revises: fix_duplicate_refresh_token
Create Date: 2026-05-04 13:29:06.669378
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '319072f585af'
down_revision: Union[str, None] = 'fix_duplicate_refresh_token'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление полей для согласия на обработку персональных данных"""
    op.add_column('qa_users', sa.Column('consent_privacy_policy', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('qa_users', sa.Column('consent_privacy_policy_date', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Откат добавления полей согласия"""
    op.drop_column('qa_users', 'consent_privacy_policy_date')
    op.drop_column('qa_users', 'consent_privacy_policy')
