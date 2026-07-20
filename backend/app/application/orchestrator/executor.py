from typing import Any, Protocol

from app.domain.models.task import Task


class TaskExecutor(Protocol):
    """What the Orchestrator needs from something that can run a task.

    Phase 3 introduces the full `Agent` Protocol from
    docs/agent-architecture.md §2; agents will be adapted to satisfy this
    same shape (`execute(task) -> dict`) so the Orchestrator doesn't need to
    change when real agents replace the echo executor used for Phase 2.
    """

    async def execute(self, task: Task) -> dict[str, Any]: ...
