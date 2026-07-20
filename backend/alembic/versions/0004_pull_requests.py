"""pull_requests table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pull_requests",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", sa.Uuid(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("repository_url", sa.String(length=500), nullable=False),
        sa.Column("branch_name", sa.String(length=200), nullable=False),
        sa.Column("commit_summary", sa.String(length=500), nullable=False),
        sa.Column("finding_ids", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("pull_requests")
