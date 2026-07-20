from app.domain.enums.task_status import TaskStatus

_ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.PENDING},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: {TaskStatus.PENDING},
}


class InvalidTaskTransitionError(Exception):
    def __init__(self, current: TaskStatus, target: TaskStatus) -> None:
        super().__init__(f"Cannot transition task from {current.value} to {target.value}")
        self.current = current
        self.target = target


def assert_valid_transition(current: TaskStatus, target: TaskStatus) -> None:
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidTaskTransitionError(current, target)
