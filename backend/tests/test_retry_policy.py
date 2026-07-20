import uuid
from datetime import datetime, timezone

from app.domain.enums.task_status import TaskStatus
from app.domain.models.task import Task
from app.domain.policies.retry_policy import backoff_seconds, should_retry


def _task(attempt: int, max_attempts: int = 3) -> Task:
    now = datetime.now(timezone.utc)
    return Task(
        id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        capability="technical_seo",
        status=TaskStatus.RUNNING,
        attempt=attempt,
        max_attempts=max_attempts,
        created_at=now,
        updated_at=now,
    )


def test_should_retry_while_attempts_remain():
    assert should_retry(_task(attempt=0, max_attempts=3)) is True
    assert should_retry(_task(attempt=2, max_attempts=3)) is True


def test_should_not_retry_once_attempts_exhausted():
    assert should_retry(_task(attempt=3, max_attempts=3)) is False


def test_backoff_grows_exponentially_and_is_capped():
    assert backoff_seconds(0, base=1.0, cap=100.0) == 1.0
    assert backoff_seconds(1, base=1.0, cap=100.0) == 2.0
    assert backoff_seconds(2, base=1.0, cap=100.0) == 4.0
    assert backoff_seconds(10, base=1.0, cap=5.0) == 5.0
