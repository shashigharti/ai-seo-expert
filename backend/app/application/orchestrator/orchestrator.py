import asyncio
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from app.application.orchestrator.executor import TaskExecutor
from app.application.validation.schema_validator import validate_agent_result
from app.config.logging import get_logger
from app.domain.enums.task_status import TaskStatus
from app.domain.errors import user_facing_message
from app.domain.models.event import WorkflowEvent
from app.domain.models.task import Task
from app.domain.policies.retry_policy import backoff_seconds, should_retry
from app.domain.policies.task_state_machine import assert_valid_transition
from app.ports.event_publisher import EventPublisher
from app.ports.repositories import TaskRepository

logger = get_logger(__name__)

DEFAULT_TASK_TIMEOUT_SECONDS = 30.0

CompletionEventDataBuilder = Callable[[Task], "dict[str, Any] | None"]


class Orchestrator:
    """Owns workflow execution: persisting task state, dispatching work,
    retrying failures, and publishing progress events. See
    docs/architecture.md §5 'Orchestrator'.

    Generic over what a task's output actually looks like: `completion_event_data`
    defaults to the SEO Agent Execution Panel's enrichment (`_completion_event_data`
    below, which parses task.output as an `AgentResult`), but any other domain
    dispatching tasks through this same Orchestrator (e.g. PR generation, whose
    output is shaped differently - status/url/branch_name, not agent_name/findings)
    can inject its own builder instead.
    """

    def __init__(
        self,
        task_repository: TaskRepository,
        event_publisher: EventPublisher,
        timeout_seconds: float = DEFAULT_TASK_TIMEOUT_SECONDS,
        completion_event_data: CompletionEventDataBuilder | None = None,
    ) -> None:
        self.task_repository = task_repository
        self.event_publisher = event_publisher
        self.timeout_seconds = timeout_seconds
        self._completion_event_data = completion_event_data or _completion_event_data

    async def create_task(
        self, workflow_id: uuid.UUID, capability: str, input: dict[str, Any]
    ) -> Task:
        now = datetime.now(timezone.utc)
        task = Task(
            id=uuid.uuid4(),
            workflow_id=workflow_id,
            capability=capability,
            status=TaskStatus.PENDING,
            input=input,
            created_at=now,
            updated_at=now,
        )
        created = await self.task_repository.create(task)
        await self.event_publisher.publish(
            WorkflowEvent(
                type="task.created",
                workflow_id=workflow_id,
                task_id=created.id,
                capability=created.capability,
                status=created.status.value,
            )
        )
        return created

    async def dispatch(self, task: Task, executor: TaskExecutor) -> Task:
        """Run a task through the executor, retrying on failure until it
        reaches a terminal state (COMPLETED or FAILED), with a timeout per
        attempt.

        This is a loop, not a single attempt - `_handle_failure` deciding to
        retry (sleeping the backoff, flipping the task back to PENDING) is
        useless unless something actually re-dispatches it afterward, and
        this is the only call site for `dispatch()` in the codebase. A
        `PENDING` task that never gets a second attempt is indistinguishable
        in the UI from one that simply hasn't started yet - it would sit at
        "Waiting" forever. Spawning the executor via `asyncio.wait_for` per
        attempt still enforces a wall-clock timeout independent of the
        executor's own internals - the "spawning workers" / "retries and
        timeouts" responsibility from docs/architecture.md §5.
        """
        while True:
            assert_valid_transition(task.status, TaskStatus.RUNNING)
            task = task.model_copy(
                update={
                    "status": TaskStatus.RUNNING,
                    # Only set on first dispatch - preserves the original start
                    # time across a retry, so "duration" reflects total elapsed
                    # work, not just the most recent attempt.
                    "started_at": task.started_at or datetime.now(timezone.utc),
                }
            )
            task = await self.task_repository.update(task)
            await self._notify(task, "task.started")

            try:
                # Broad on purpose: asyncio.TimeoutError and any executor-raised
                # exception are both retryable failures from the orchestrator's
                # point of view.
                output = await asyncio.wait_for(executor.execute(task), timeout=self.timeout_seconds)
            except Exception as exc:
                logger.warning("Task %s failed: %s", task.id, exc)
                task = await self._handle_failure(task, exc)
                if task.status == TaskStatus.PENDING:
                    continue  # _handle_failure already slept the backoff
                return task  # FAILED - attempts exhausted

            task = task.model_copy(update={"status": TaskStatus.COMPLETED, "output": output})
            task = await self.task_repository.update(task)
            await self._notify(task, "task.completed", data=self._completion_event_data(task))
            return task

    async def _handle_failure(self, task: Task, exc: Exception) -> Task:
        attempt = task.attempt + 1
        failing_task = task.model_copy(update={"attempt": attempt})

        if should_retry(failing_task):
            await asyncio.sleep(backoff_seconds(attempt))
            retried = failing_task.model_copy(update={"status": TaskStatus.PENDING})
            retried = await self.task_repository.update(retried)
            await self._notify(retried, "task.retrying")
            return retried

        # Only the final, non-retryable failure gets an error_message -
        # an intermediate retry isn't a failure the user needs to see.
        message = user_facing_message(exc)
        failed = failing_task.model_copy(update={"status": TaskStatus.FAILED, "error_message": message})
        failed = await self.task_repository.update(failed)
        await self._notify(failed, "task.failed", data={"error_message": message})
        return failed

    async def resume_pending_tasks(self, workflow_id: uuid.UUID) -> list[Task]:
        """Return tasks left PENDING or RUNNING for a workflow - candidates
        for re-dispatch after an interrupted process restart.
        """
        tasks = await self.task_repository.list_for_workflow(workflow_id)
        return [t for t in tasks if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)]

    async def _notify(self, task: Task, event_type: str, data: dict[str, Any] | None = None) -> None:
        await self.event_publisher.publish(
            WorkflowEvent(
                type=event_type,
                workflow_id=task.workflow_id,
                task_id=task.id,
                capability=task.capability,
                status=task.status.value,
                data=data,
            )
        )


def _completion_event_data(task: Task) -> dict[str, Any] | None:
    """Enriches a task.completed event with the Agent Execution Panel's
    per-agent fields (docs/specs.md §4) - agent name, confidence, tokens,
    model, duration. Parses task.output the same way
    analysis_runner._review_and_persist does (validate_agent_result), so one
    malformed output doesn't crash event publishing - returns None rather
    than raising, same failure mode as the review pipeline's own parsing.
    """
    result = validate_agent_result(task.output or {})
    if result is None:
        return None
    return {
        "agent_name": result.agent_name,
        "confidence": result.confidence,
        "token_usage": result.token_usage.model_dump() if result.token_usage else None,
        "model": result.model,
        "findings_count": len(result.findings),
        "limitations": result.limitations,
        "duration_seconds": (
            (task.updated_at - task.started_at).total_seconds() if task.started_at else None
        ),
        "reasoning": result.reasoning,
    }
