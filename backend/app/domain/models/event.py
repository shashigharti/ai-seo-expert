from typing import Any
from uuid import UUID

from pydantic import BaseModel


class WorkflowEvent(BaseModel):
    """Matches the event shape in docs/api-contracts.md 'Stream Workflow Events'."""

    type: str
    workflow_id: UUID
    task_id: UUID | None = None
    capability: str | None = None
    status: str | None = None
    data: dict[str, Any] | None = None
