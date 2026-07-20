from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Approval(BaseModel):
    """Audit trail entry - docs/implementation.md Phase 7 "audit trail",
    docs/api-contracts.md "Approve Fixes".
    """

    id: UUID
    workflow_id: UUID
    finding_ids: list[UUID]
    pr_strategy: str
    created_at: datetime

    model_config = {"from_attributes": True}
