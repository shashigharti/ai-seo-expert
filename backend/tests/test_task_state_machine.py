import pytest

from app.domain.enums.task_status import TaskStatus
from app.domain.policies.task_state_machine import InvalidTaskTransitionError, assert_valid_transition


def test_pending_to_running_is_allowed():
    assert_valid_transition(TaskStatus.PENDING, TaskStatus.RUNNING)


def test_running_to_completed_is_allowed():
    assert_valid_transition(TaskStatus.RUNNING, TaskStatus.COMPLETED)


def test_running_to_failed_is_allowed():
    assert_valid_transition(TaskStatus.RUNNING, TaskStatus.FAILED)


def test_failed_to_pending_is_allowed_for_retry():
    assert_valid_transition(TaskStatus.FAILED, TaskStatus.PENDING)


def test_completed_is_terminal():
    with pytest.raises(InvalidTaskTransitionError):
        assert_valid_transition(TaskStatus.COMPLETED, TaskStatus.RUNNING)


def test_pending_cannot_skip_to_completed():
    with pytest.raises(InvalidTaskTransitionError):
        assert_valid_transition(TaskStatus.PENDING, TaskStatus.COMPLETED)
