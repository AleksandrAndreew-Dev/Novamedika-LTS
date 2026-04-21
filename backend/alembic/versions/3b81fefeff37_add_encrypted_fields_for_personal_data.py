"""add_encrypted_fields_for_personal_data

Revision ID: 3b81fefeff37
Revises: m3n4o5p6q7r8
Create Date: 2026-04-21 16:03:35.786758

Эта миграция добавляет зашифрованные поля для персональных данных согласно требованиям ОАЦ:
- telegram_id_encrypted в qa_users и booking_orders
- phone_encrypted в qa_users
- customer_phone_encrypted в booking_orders

После добавления полей, существующие данные шифруются и переносятся в новые поля.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3b81fefeff37'
down_revision: Union[str, None] = 'm3n4o5p6q7r8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить зашифрованные поля и перенести данные"""
    
    # === Шаг 1: Добавить новые зашифрованные поля ===
    
    # Для таблицы qa_users
    op.add_column('qa_users', sa.Column('telegram_id_encrypted', sa.String(255), nullable=True))
    op.add_column('qa_users', sa.Column('phone_encrypted', sa.String(255), nullable=True))
    
    # Создаем индексы для encrypted полей
    op.create_index('idx_qa_users_telegram_id_encrypted', 'qa_users', ['telegram_id_encrypted'], unique=True)
    
    # Для таблицы booking_orders
    op.add_column('booking_orders', sa.Column('customer_phone_encrypted', sa.String(255), nullable=True))
    op.add_column('booking_orders', sa.Column('telegram_id_encrypted', sa.String(255), nullable=True))
    
    # Создаем индекс для telegram_id_encrypted в booking_orders
    op.create_index('idx_booking_orders_telegram_id_encrypted', 'booking_orders', ['telegram_id_encrypted'])
    
    # === Шаг 2: Зашифровать существующие данные ===
    
    # Шифрование данных в qa_users
    op.execute("""
        UPDATE qa_users 
        SET telegram_id_encrypted = ENCODE(
            pgp_sym_encrypt(telegram_id::text, current_setting('app.encryption_key')),
            'base64'
        )
        WHERE telegram_id IS NOT NULL
    """)
    
    op.execute("""
        UPDATE qa_users 
        SET phone_encrypted = ENCODE(
            pgp_sym_encrypt(phone, current_setting('app.encryption_key')),
            'base64'
        )
        WHERE phone IS NOT NULL
    """)
    
    # Шифрование данных в booking_orders
    op.execute("""
        UPDATE booking_orders 
        SET customer_phone_encrypted = ENCODE(
            pgp_sym_encrypt(customer_phone, current_setting('app.encryption_key')),
            'base64'
        )
        WHERE customer_phone IS NOT NULL
    """)
    
    op.execute("""
        UPDATE booking_orders 
        SET telegram_id_encrypted = ENCODE(
            pgp_sym_encrypt(telegram_id::text, current_setting('app.encryption_key')),
            'base64'
        )
        WHERE telegram_id IS NOT NULL
    """)


def downgrade() -> None:
    """Удалить зашифрованные поля"""
    
    # Удаляем индексы
    op.drop_index('idx_booking_orders_telegram_id_encrypted', table_name='booking_orders')
    op.drop_index('idx_qa_users_telegram_id_encrypted', table_name='qa_users')
    
    # Удаляем зашифрованные поля
    op.drop_column('booking_orders', 'telegram_id_encrypted')
    op.drop_column('booking_orders', 'customer_phone_encrypted')
    op.drop_column('qa_users', 'phone_encrypted')
    op.drop_column('qa_users', 'telegram_id_encrypted')
