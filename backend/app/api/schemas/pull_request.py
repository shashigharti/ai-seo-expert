from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class PullRequestResponse(BaseModel):
    id: UUID
    workflow_id: UUID
    status: Literal["opened", "failed"]
    url: str | None
    repository_url: str
    branch_name: str
    commit_summary: str
    finding_ids: list[UUID]
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PullRequestListResponse(BaseModel):
    items: list[PullRequestResponse]


class PullRequestGenerationStartedResponse(BaseModel):
    """POST /pull-requests's response - generation now runs in the
    background (see PullRequestService.start_generation), so this returns
    immediately with the task ids to watch rather than final results.
    Final results are fetched via GET /pull-requests once tasks complete,
    or observed live via GET /events (the GitHub PR Agent Execution panel).
    """

    task_ids: list[UUID]
