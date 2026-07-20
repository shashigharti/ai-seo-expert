from typing import Literal

from pydantic import BaseModel, Field

from app.domain.models.task_brief import TaskBrief


class PlannedCapability(BaseModel):
    """What the manager's model decides needs analyzing - narrower than a
    full TaskBrief; id/workflow_id are filled in by code, not the LLM.
    """

    capability: str
    objective: str
    scope: dict[str, list[str]] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    priority: Literal["low", "medium", "high"] = "medium"


class SEOPlanOutput(BaseModel):
    """LLM structured output for the manager's initial planning pass."""

    capabilities: list[PlannedCapability]
    rationale: str


class SEOEvaluationOutput(BaseModel):
    """LLM structured output for the manager's post-results evaluation pass.

    docs/agent-architecture.md §7: workers only suggest follow-ups; the
    manager decides whether to convert a suggestion into a real task.
    """

    is_complete: bool
    rationale: str
    follow_up_capabilities: list[PlannedCapability] = Field(default_factory=list)


class ManagerDecision(BaseModel):
    """Manager's decision after evaluating worker results, with follow-up
    suggestions already converted into full TaskBriefs.
    """

    is_complete: bool
    rationale: str
    follow_up_briefs: list[TaskBrief] = Field(default_factory=list)
