from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums.task_status import TaskStatus
from app.domain.models.agent_result import AgentResult
from app.domain.models.task import Task
from app.domain.policies.cost_estimation import estimate_cost_usd


class TokenUsageResponse(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int
    reasoning_tokens: int | None = None


class TaskResponse(BaseModel):
    """Backs the Agent Execution Panel (docs/specs.md §4): an initial
    snapshot on page load, joined against live SSE deltas from
    GET /{workflow_id}/events. The agent_name/confidence/token_usage/model/
    estimated_cost_usd fields are only populated once task.output parses as
    a valid AgentResult (see `_task_to_response` in the route) - they're
    None/absent for a task that hasn't completed yet.
    """

    id: UUID
    workflow_id: UUID
    capability: str
    status: TaskStatus
    attempt: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    agent_name: str | None = None
    confidence: float | None = None
    token_usage: TokenUsageResponse | None = None
    model: str | None = None
    estimated_cost_usd: float | None = None
    findings_count: int | None = None
    limitations: list[str] = []
    error_message: str | None = None
    reasoning: str | None = None


class TaskListResponse(BaseModel):
    items: list[TaskResponse]


def task_to_response(task: Task, result: AgentResult | None) -> TaskResponse:
    token_usage = None
    estimated_cost_usd = None
    if result is not None and result.token_usage is not None:
        token_usage = TokenUsageResponse(
            input_tokens=result.token_usage.input_tokens,
            output_tokens=result.token_usage.output_tokens,
            total_tokens=result.token_usage.total_tokens,
            reasoning_tokens=result.token_usage.reasoning_tokens,
        )
        estimated_cost_usd = estimate_cost_usd(result.model, result.token_usage)

    return TaskResponse(
        id=task.id,
        workflow_id=task.workflow_id,
        capability=task.capability,
        status=task.status,
        attempt=task.attempt,
        max_attempts=task.max_attempts,
        created_at=task.created_at,
        updated_at=task.updated_at,
        started_at=task.started_at,
        agent_name=result.agent_name if result else None,
        confidence=result.confidence if result else None,
        token_usage=token_usage,
        model=result.model if result else None,
        estimated_cost_usd=estimated_cost_usd,
        findings_count=len(result.findings) if result else None,
        limitations=result.limitations if result else [],
        error_message=task.error_message,
        reasoning=result.reasoning if result else None,
    )
