from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.domain.enums.workflow_status import WorkflowStatus
from app.domain.models.workflow import DEFAULT_GOAL


class WorkflowCreateRequest(BaseModel):
    repository_url: HttpUrl
    branch: str = Field(default="master", min_length=1, max_length=255)
    goal: str = Field(default=DEFAULT_GOAL, min_length=1, max_length=2000)


class WorkflowResponse(BaseModel):
    id: UUID
    repository_url: str
    branch: str
    goal: str
    status: WorkflowStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Matches docs/api-contracts.md's error envelope."""

    error: ErrorDetail
