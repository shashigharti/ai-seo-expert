from app.domain.models.task import Task


def should_retry(task: Task) -> bool:
    """A task is retryable if it hasn't yet used all of its attempts."""
    return task.attempt < task.max_attempts


def backoff_seconds(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    """Exponential backoff: base * 2^attempt, capped."""
    return min(base * (2**attempt), cap)
