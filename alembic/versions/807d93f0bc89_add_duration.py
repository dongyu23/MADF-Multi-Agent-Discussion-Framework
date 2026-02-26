"""add_duration

Revision ID: 807d93f0bc89
Revises: 069626729e0d
Create Date: 2026-02-26 20:58:35.095598

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '807d93f0bc89'
down_revision = '069626729e0d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('forums', schema=None) as batch_op:
        batch_op.add_column(sa.Column('duration_minutes', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('forums', schema=None) as batch_op:
        batch_op.drop_column('duration_minutes')
