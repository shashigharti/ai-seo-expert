import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.events.sse_publisher import SSEEventPublisher
from app.adapters.postgres.repositories.task_repository import PostgresTaskRepository
from app.application.orchestrator.echo_executor import EchoTaskExecutor
from app.application.orchestrator.orchestrator import Orchestrator
from app.domain.enums.task_status import TaskStatus
from app.domain.errors import ExternalErrorKind, ExternalServiceError
from app.domain.models.event import WorkflowEvent
from app.domain.models.task import Task


class AlwaysFailsExecutor:
    async def execute(self, task: Task) -> dict[str, Any]:
        raise RuntimeError("boom")


class AlwaysFailsWithClassifiedErrorExecutor:
    async def execute(self, task: Task) -> dict[str, Any]:
        raise ExternalServiceError(
            service="Qwen Cloud", kind=ExternalErrorKind.AUTH, message="Qwen Cloud rejected the API key."
        )


class FailsThenSucceedsExecutor:
    """Fails transiently a fixed number of times, then succeeds - proves
    Orchestrator.dispatch actually retries internally rather than handing
    back a PENDING task nobody ever re-dispatches (the bug this fixes)."""

    def __init__(self, fail_count: int) -> None:
        self.fail_count = fail_count
        self.calls = 0

    async def execute(self, task: Task) -> dict[str, Any]:
        self.calls += 1
        if self.calls <= self.fail_count:
            raise RuntimeError("transient failure")
        return {"echo": "ok"}


class _AgentResultExecutor:
    """Returns a real AgentResult-shaped dict (unlike EchoTaskExecutor),
    so the orchestrator's task.completed event-enrichment logic
    (_completion_event_data) has something valid to parse.
    """

    async def execute(self, task: Task) -> dict[str, Any]:
        return {
            "task_id": str(task.id),
            "agent_name": "TechnicalSEOAgent",
            "status": "completed",
            "findings": [],
            "confidence": 0.9,
            "limitations": [],
            "follow_up_suggestions": [],
            "token_usage": {"input_tokens": 10, "output_tokens": 5},
            "model": "qwen-plus",
        }


class _RecordingEventPublisher:
    def __init__(self) -> None:
        self.events: list[WorkflowEvent] = []

    async def publish(self, event: WorkflowEvent) -> None:
        self.events.append(event)


@pytest.fixture
def orchestrator(db_session: AsyncSession) -> Orchestrator:
    return Orchestrator(
        task_repository=PostgresTaskRepository(db_session),
        event_publisher=SSEEventPublisher(),
        timeout_seconds=5.0,
    )


async def test_create_task_persists_pending_task(orchestrator: Orchestrator):
    workflow_id = uuid.uuid4()
    task = await orchestrator.create_task(workflow_id, "technical_seo", {"url": "https://example.com"})

    assert task.status == TaskStatus.PENDING
    assert task.workflow_id == workflow_id


async def test_dispatch_success_marks_task_completed(orchestrator: Orchestrator):
    task = await orchestrator.create_task(uuid.uuid4(), "technical_seo", {"url": "https://example.com"})

    result = await orchestrator.dispatch(task, EchoTaskExecutor())

    assert result.status == TaskStatus.COMPLETED
    assert result.output == {"echo": {"url": "https://example.com"}, "capability": "technical_seo"}


async def test_dispatch_retries_internally_until_attempts_exhausted(orchestrator: Orchestrator):
    """A single dispatch() call must retry on its own - nothing else in the
    codebase ever calls dispatch() again for an already-created task, so if
    dispatch() itself doesn't loop, a retryable failure is retried exactly
    zero times in practice, no matter what the retry policy says."""
    task = await orchestrator.create_task(uuid.uuid4(), "technical_seo", {})
    assert task.max_attempts == 3

    result = await orchestrator.dispatch(task, AlwaysFailsExecutor())

    assert result.status == TaskStatus.FAILED
    assert result.attempt == 3


async def test_dispatch_retries_and_eventually_succeeds(orchestrator: Orchestrator):
    executor = FailsThenSucceedsExecutor(fail_count=2)

    task = await orchestrator.create_task(uuid.uuid4(), "technical_seo", {})
    result = await orchestrator.dispatch(task, executor)

    assert result.status == TaskStatus.COMPLETED
    assert result.output == {"echo": "ok"}
    assert executor.calls == 3


async def test_dispatch_failure_marks_failed_once_attempts_exhausted(orchestrator: Orchestrator):
    task = await orchestrator.create_task(uuid.uuid4(), "technical_seo", {})
    task = task.model_copy(update={"max_attempts": 1})
    task = await orchestrator.task_repository.update(task)

    result = await orchestrator.dispatch(task, AlwaysFailsExecutor())

    assert result.status == TaskStatus.FAILED
    assert result.attempt == 1
    # An unclassified exception ("boom") must never leak into error_message -
    # only a classified ExternalServiceError's curated .message is safe to
    # surface (see the next test).
    assert result.error_message == "An unexpected error occurred. Check server logs for details."


async def test_dispatch_failure_records_curated_message_for_classified_error(orchestrator: Orchestrator):
    task = await orchestrator.create_task(uuid.uuid4(), "technical_seo", {})
    task = task.model_copy(update={"max_attempts": 1})
    task = await orchestrator.task_repository.update(task)

    result = await orchestrator.dispatch(task, AlwaysFailsWithClassifiedErrorExecutor())

    assert result.status == TaskStatus.FAILED
    assert result.error_message == "Qwen Cloud rejected the API key."


async def test_dispatch_does_not_set_error_message_on_an_intermediate_retry(db_session: AsyncSession):
    """The mid-retry PENDING state isn't observable via dispatch()'s return
    value anymore (retries happen internally now - see
    test_dispatch_retries_internally_until_attempts_exhausted) - only the
    event stream shows it: task.retrying must carry no error_message, since
    an intermediate attempt failing isn't something the user needs to see;
    only the final task.failed does.
    """
    publisher = _RecordingEventPublisher()
    orchestrator = Orchestrator(
        task_repository=PostgresTaskRepository(db_session), event_publisher=publisher, timeout_seconds=5.0
    )
    task = await orchestrator.create_task(uuid.uuid4(), "technical_seo", {})

    result = await orchestrator.dispatch(task, AlwaysFailsExecutor())

    assert result.status == TaskStatus.FAILED
    retrying_events = [e for e in publisher.events if e.type == "task.retrying"]
    assert len(retrying_events) == 2  # max_attempts=3 -> 2 retries before the final failure
    assert all(e.data is None for e in retrying_events)

    [failed_event] = [e for e in publisher.events if e.type == "task.failed"]
    assert failed_event.data["error_message"] == result.error_message


async def test_resume_pending_tasks_returns_incomplete_tasks_only(orchestrator: Orchestrator):
    workflow_id = uuid.uuid4()
    pending_task = await orchestrator.create_task(workflow_id, "metadata", {})
    completed_task = await orchestrator.create_task(workflow_id, "content_seo", {})
    await orchestrator.dispatch(completed_task, EchoTaskExecutor())

    resumable = await orchestrator.resume_pending_tasks(workflow_id)

    resumable_ids = {t.id for t in resumable}
    assert pending_task.id in resumable_ids
    assert completed_task.id not in resumable_ids


async def test_dispatch_sets_started_at_once_and_preserves_it_across_internal_retries(
    orchestrator: Orchestrator,
):
    """Retries must not reset started_at on each attempt - otherwise a
    task's reported duration would reflect only its last attempt, not the
    total elapsed work across all of them."""
    started_at_per_attempt: list = []

    class _CapturingExecutor:
        def __init__(self, fail_count: int) -> None:
            self.fail_count = fail_count
            self.calls = 0

        async def execute(self, task: Task) -> dict[str, Any]:
            started_at_per_attempt.append(task.started_at)
            self.calls += 1
            if self.calls <= self.fail_count:
                raise RuntimeError("transient failure")
            return {"echo": "ok"}

    task = await orchestrator.create_task(uuid.uuid4(), "technical_seo", {})
    assert task.started_at is None

    result = await orchestrator.dispatch(task, _CapturingExecutor(fail_count=2))

    assert result.status == TaskStatus.COMPLETED
    assert result.started_at is not None
    assert len(started_at_per_attempt) == 3
    assert started_at_per_attempt == [result.started_at] * 3


async def test_dispatch_completion_event_carries_capability_and_enriched_data(db_session: AsyncSession):
    publisher = _RecordingEventPublisher()
    orchestrator = Orchestrator(
        task_repository=PostgresTaskRepository(db_session), event_publisher=publisher, timeout_seconds=5.0
    )
    task = await orchestrator.create_task(uuid.uuid4(), "technical_seo", {})

    result = await orchestrator.dispatch(task, _AgentResultExecutor())

    assert result.status == TaskStatus.COMPLETED
    completed_events = [e for e in publisher.events if e.type == "task.completed"]
    assert len(completed_events) == 1
    event = completed_events[0]
    assert event.capability == "technical_seo"
    assert event.data is not None
    assert event.data["agent_name"] == "TechnicalSEOAgent"
    assert event.data["confidence"] == 0.9
    assert event.data["model"] == "qwen-plus"
    assert event.data["token_usage"] == {"input_tokens": 10, "output_tokens": 5, "reasoning_tokens": None}
    assert event.data["duration_seconds"] is not None
    assert event.data["reasoning"] is None


async def test_dispatch_completion_event_carries_reasoning_when_present(db_session: AsyncSession):
    class _ThinkingAgentResultExecutor:
        async def execute(self, task: Task) -> dict[str, Any]:
            return {
                "task_id": str(task.id),
                "agent_name": "AccessibilityAgent",
                "status": "completed",
                "findings": [],
                "confidence": 0.9,
                "limitations": [],
                "follow_up_suggestions": [],
                "token_usage": {"input_tokens": 10, "output_tokens": 40, "reasoning_tokens": 25},
                "model": "qwen-plus",
                "reasoning": "Checked the <html> tag for a lang attribute; none found.",
            }

    publisher = _RecordingEventPublisher()
    orchestrator = Orchestrator(
        task_repository=PostgresTaskRepository(db_session), event_publisher=publisher, timeout_seconds=5.0
    )
    task = await orchestrator.create_task(uuid.uuid4(), "accessibility", {})

    await orchestrator.dispatch(task, _ThinkingAgentResultExecutor())

    [event] = [e for e in publisher.events if e.type == "task.completed"]
    assert event.data["reasoning"] == "Checked the <html> tag for a lang attribute; none found."
    assert event.data["token_usage"]["reasoning_tokens"] == 25


async def test_dispatch_completion_event_has_no_data_when_output_is_not_a_valid_agent_result(
    orchestrator: Orchestrator,
):
    """EchoTaskExecutor's output doesn't match AgentResult's schema - the
    event should still publish, just without the enriched data payload,
    rather than crashing task completion over a malformed output.
    """
    task = await orchestrator.create_task(uuid.uuid4(), "technical_seo", {"url": "https://example.com"})

    result = await orchestrator.dispatch(task, EchoTaskExecutor())

    assert result.status == TaskStatus.COMPLETED


async def test_dispatch_uses_injected_completion_event_data_builder(db_session: AsyncSession):
    """A caller outside the SEO analysis domain (e.g. PR generation, whose
    task.output is shaped completely differently - status/url/branch_name,
    not agent_name/findings) can inject its own completion-event-data
    builder instead of the default AgentResult-shaped one.
    """
    publisher = _RecordingEventPublisher()
    orchestrator = Orchestrator(
        task_repository=PostgresTaskRepository(db_session),
        event_publisher=publisher,
        timeout_seconds=5.0,
        completion_event_data=lambda task: {"custom": True, "output_keys": sorted(task.output or {})},
    )
    task = await orchestrator.create_task(uuid.uuid4(), "pull_request_metadata", {})

    class _PRShapedExecutor:
        async def execute(self, task: Task) -> dict[str, Any]:
            return {"status": "opened", "url": "https://github.com/example/project/pull/1"}

    result = await orchestrator.dispatch(task, _PRShapedExecutor())

    assert result.status == TaskStatus.COMPLETED
    [event] = [e for e in publisher.events if e.type == "task.completed"]
    assert event.data == {"custom": True, "output_keys": ["status", "url"]}


async def test_dispatch_defaults_to_agent_result_completion_event_data_when_no_builder_injected(
    db_session: AsyncSession,
):
    """Confirms omitting `completion_event_data` keeps today's behavior
    unchanged for every existing caller (SEO analysis)."""
    publisher = _RecordingEventPublisher()
    orchestrator = Orchestrator(
        task_repository=PostgresTaskRepository(db_session), event_publisher=publisher, timeout_seconds=5.0
    )
    task = await orchestrator.create_task(uuid.uuid4(), "technical_seo", {})

    await orchestrator.dispatch(task, _AgentResultExecutor())

    [event] = [e for e in publisher.events if e.type == "task.completed"]
    assert event.data["agent_name"] == "TechnicalSEOAgent"
