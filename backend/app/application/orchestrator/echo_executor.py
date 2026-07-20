from typing import Any

from app.domain.models.task import Task


class EchoTaskExecutor:
    """Deterministic executor with no LLM dependency - used to exercise the
    Orchestrator's dispatch/retry/event-publishing mechanics (Phase 2) before
    real agents exist (Phase 3+). Echoes the task input back as output.
    """

    async def execute(self, task: Task) -> dict[str, Any]:
        return {"echo": task.input, "capability": task.capability}
