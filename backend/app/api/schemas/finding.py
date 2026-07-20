from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums.finding_status import FindingStatus
from app.domain.models.agent_result import Finding


class FindingResponse(BaseModel):
    id: UUID
    workflow_id: UUID
    task_id: UUID
    agent_name: str
    finding: Finding
    status: FindingStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class FindingListResponse(BaseModel):
    total: int
    findings_by_category: dict[str, int]
    findings_by_severity: dict[str, int]
    items: list[FindingResponse]


class ApprovalRequest(BaseModel):
    finding_ids: list[UUID] = Field(min_length=1)
    pr_strategy: str = "by_category"


class ApprovalResponse(BaseModel):
    id: UUID
    workflow_id: UUID
    finding_ids: list[UUID]
    pr_strategy: str
    created_at: datetime

    model_config = {"from_attributes": True}
