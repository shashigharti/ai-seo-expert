from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class PullRequestResult(BaseModel):
    """docs/specs.md §3 Automated Fix - PR status, URL, repository, branch,
    commit summary shown to the user."""

    id: UUID
    workflow_id: UUID
    status: Literal["opened", "failed"]
    url: str | None
    repository_url: str
    branch_name: str
    commit_summary: str
    finding_ids: list[UUID]
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
