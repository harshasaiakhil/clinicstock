"""add force_password_change to users

Revision ID: c1f2e3d4a5b6
Revises: b9e41e1ee0dd
Create Date: 2026-11-23 17:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c1f2e3d4a5b6'
down_revision: Union[str, None] = 'b9e41e1ee0dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('force_password_change', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )

def downgrade() -> None:
    op.drop_column('users', 'force_password_change')
