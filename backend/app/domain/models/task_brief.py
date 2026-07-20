from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TaskBrief(BaseModel):
    """docs/agent-architecture.md §8 - what the SEO Manager hands the
    Orchestrator for each task it decides to create.
    """

    id: UUID
    workflow_id: UUID
    capability: str
    objective: str
    scope: dict[str, list[str]] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    expected_output: str
    priority: Literal["low", "medium", "high"] = "medium"
    depends_on: list[UUID] = Field(default_factory=list)
