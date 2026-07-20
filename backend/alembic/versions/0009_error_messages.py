"""workflows/tasks: add error_message

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("error_message", sa.String(length=2000), nullable=True))
    op.add_column("tasks", sa.Column("error_message", sa.String(length=2000), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "error_message")
    op.drop_column("workflows", "error_message")
