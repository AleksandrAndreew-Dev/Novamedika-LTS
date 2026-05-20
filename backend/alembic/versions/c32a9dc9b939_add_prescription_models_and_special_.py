"""add_prescription_models_and_special_data_consent

Revision ID: c32a9dc9b939
Revises: 85d18caad27f
Create Date: 2026-05-20 07:49:26.616800
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c32a9dc9b939'
down_revision: Union[str, None] = '85d18caad27f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create prescriptions table
    op.create_table(
        'prescriptions',
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('answered_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('pharmacist_response', sa.Text(), nullable=True),
        sa.Column('pharmacist_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('auto_delete_scheduled', sa.Boolean(), nullable=False),
        sa.Column('auto_delete_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['pharmacist_id'], ['qa_pharmacists.uuid'], ),
        sa.ForeignKeyConstraint(['user_id'], ['qa_users.uuid'], ),
        sa.PrimaryKeyConstraint('uuid')
    )
    
    # Create indexes for prescriptions table
    op.create_index('idx_prescription_user_id', 'prescriptions', ['user_id'])
    op.create_index('idx_prescription_status', 'prescriptions', ['status'])
    op.create_index('idx_prescription_auto_delete_at', 'prescriptions', ['auto_delete_at'])
    
    # Add special data consent fields to qa_users table
    op.add_column('qa_users', 
        sa.Column('consent_special_data', sa.Boolean(), nullable=False, server_default='false',
                  comment='Согласие на обработку специальных ПД (сведений о здоровье)'))
    op.add_column('qa_users',
        sa.Column('consent_special_data_date', sa.DateTime(), nullable=True,
                  comment='Дата предоставления согласия на обработку специальных ПД'))


def downgrade() -> None:
    # Remove special data consent fields from qa_users table
    op.drop_column('qa_users', 'consent_special_data_date')
    op.drop_column('qa_users', 'consent_special_data')
    
    # Drop indexes for prescriptions table
    op.drop_index('idx_prescription_auto_delete_at', table_name='prescriptions')
    op.drop_index('idx_prescription_status', table_name='prescriptions')
    op.drop_index('idx_prescription_user_id', table_name='prescriptions')
    
    # Drop prescriptions table
    op.drop_table('prescriptions')
