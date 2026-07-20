from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums.task_status import TaskStatus


class Task(BaseModel):
    """Core domain representation of a unit of work dispatched by the Orchestrator."""

    id: UUID
    workflow_id: UUID
    capability: str
    status: TaskStatus
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    attempt: int = 0
    max_attempts: int = 3
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
