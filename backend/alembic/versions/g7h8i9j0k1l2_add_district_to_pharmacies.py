"""add district column to pharmacies table

Revision ID: g7h8i9j0k1l2
Revises: a1b2c3d4e5f6
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g7h8i9j0k1l2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('pharmacies', sa.Column('district', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('pharmacies', 'district')
