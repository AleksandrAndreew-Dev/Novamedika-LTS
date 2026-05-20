"""add_email_and_password_fields_to_users

Revision ID: 68197b075a41
Revises: c32a9dc9b939
Create Date: 2026-05-20 08:27:00.389762
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68197b075a41'
down_revision: Union[str, None] = 'c32a9dc9b939'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email and password fields to qa_users table"""
    # Add encrypted email field
    op.add_column('qa_users', sa.Column('email_encrypted', sa.String(255), nullable=True))
    op.create_index(op.f('ix_qa_users_email_encrypted'), 'qa_users', ['email_encrypted'], unique=True)
    
    # Add unencrypted email field for backward compatibility
    op.add_column('qa_users', sa.Column('email', sa.String(255), nullable=True))
    
    # Add password hash field
    op.add_column('qa_users', sa.Column('password_hash', sa.String(255), nullable=True))


def downgrade() -> None:
    """Remove email and password fields from qa_users table"""
    op.drop_column('qa_users', 'password_hash')
    op.drop_column('qa_users', 'email')
    op.drop_index(op.f('ix_qa_users_email_encrypted'), table_name='qa_users')
    op.drop_column('qa_users', 'email_encrypted')
