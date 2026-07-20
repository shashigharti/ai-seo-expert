from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums.finding_status import FindingStatus
from app.domain.models.agent_result import Finding


class StoredFinding(BaseModel):
    """A persisted, individually-referenceable Finding.

    `Finding` itself (docs/agent-architecture.md §9) has no `id` - it's the
    LLM's output shape, and the model shouldn't be asked to invent an
    identifier. This wraps one with the identity/status/provenance needed
    once it's stored: `docs/api-contracts.md`'s approval request references
    findings by id (`finding_ids`), which requires one to exist.
    """

    id: UUID
    workflow_id: UUID
    task_id: UUID
    agent_name: str
    finding: Finding
    status: FindingStatus = FindingStatus.PENDING
    created_at: datetime

    model_config = {"from_attributes": True}
