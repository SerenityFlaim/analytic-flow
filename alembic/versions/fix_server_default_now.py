"""fix server_default now()

Revision ID: b2c3d4e5f6a7
Revises: 814a1bcffc46
Create Date: 2026-06-08 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a8'
down_revision: Union[str, Sequence[str], None] = '814a1bcffc46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'users', 'created_at',
        server_default=sa.func.now()
    )
    op.alter_column(
        'projects', 'created_at',
        server_default=sa.func.now()
    )
    op.alter_column(
        'user_scenarios', 'updated_at',
        server_default=sa.func.now()
    )
    op.alter_column(
        'analysis_results', 'created_at',
        server_default=sa.func.now()
    )


def downgrade() -> None:
    op.alter_column(
        'users', 'created_at',
        server_default='now()'
    )
    op.alter_column(
        'projects', 'created_at',
        server_default='now()'
    )
    op.alter_column(
        'user_scenarios', 'updated_at',
        server_default='now()'
    )
    op.alter_column(
        'analysis_results', 'created_at',
        server_default='now()'
    )