"""workflows: replace pull_request_number with branch

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workflows",
        sa.Column("branch", sa.String(length=255), nullable=False, server_default="master"),
    )
    op.drop_column("workflows", "pull_request_number")


def downgrade() -> None:
    op.add_column("workflows", sa.Column("pull_request_number", sa.Integer(), nullable=True))
    op.drop_column("workflows", "branch")
