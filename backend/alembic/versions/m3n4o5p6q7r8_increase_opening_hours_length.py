"""increase opening_hours column to VARCHAR(500)

Revision ID: m3n4o5p6q7r8
Revises: g7h8i9j0k1l2
Create Date: 2026-04-14
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'm3n4o5p6q7r8'
down_revision = 'g7h8i9j0k1l2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'pharmacies',
        'opening_hours',
        type_=sa.String(500),
        existing_type=sa.String(255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'pharmacies',
        'opening_hours',
        type_=sa.String(255),
        existing_type=sa.String(500),
        nullable=True,
    )
