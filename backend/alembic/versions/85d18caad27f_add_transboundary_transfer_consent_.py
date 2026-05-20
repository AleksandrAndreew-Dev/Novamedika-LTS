"""add_transboundary_transfer_consent_fields

Revision ID: 85d18caad27f
Revises: 6cfa51de7ac5
Create Date: 2026-05-20 07:24:15.513387
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85d18caad27f'
down_revision: Union[str, None] = '6cfa51de7ac5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавление полей для согласия на трансграничную передачу ПД через Telegram"""
    
    # Добавляем поле согласия на трансграничную передачу
    op.add_column('qa_users', 
        sa.Column('consent_transboundary_transfer', sa.Boolean(), 
                  nullable=False, server_default='false',
                  comment='Согласие на трансграничную передачу ПД через Telegram (UK/UAE)'))
    
    # Добавляем дату предоставления согласия
    op.add_column('qa_users', 
        sa.Column('consent_transboundary_transfer_date', sa.DateTime(), 
                  nullable=True,
                  comment='Дата и время предоставления согласия на трансграничную передачу'))
    
    # Добавляем поле подтверждения осведомленности о рисках
    op.add_column('qa_users', 
        sa.Column('transboundary_risks_acknowledged', sa.Boolean(), 
                  nullable=False, server_default='false',
                  comment='Подтверждение ознакомления с рисками трансграничной передачи'))


def downgrade() -> None:
    """Откат добавления полей согласия на трансграничную передачу"""
    op.drop_column('qa_users', 'transboundary_risks_acknowledged')
    op.drop_column('qa_users', 'consent_transboundary_transfer_date')
    op.drop_column('qa_users', 'consent_transboundary_transfer')
