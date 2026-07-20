from typing import Any

from app.agents.base import Agent
from app.domain.models.task import Task


class AgentTaskExecutorAdapter:
    """Adapts an Agent (`execute(task) -> AgentResult`) to the Orchestrator's
    TaskExecutor shape (`execute(task) -> dict`), so the result can be stored
    directly in Task.output (a JSON column). Per executor.py's note: real
    agents get adapted to the Orchestrator's shape, not the other way round.
    """

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    async def execute(self, task: Task) -> dict[str, Any]:
        result = await self._agent.execute(task)
        # AgentResult.model isn't set by any agent's own execute() - filled
        # in here, uniformly across every agent type, from whichever model
        # actually ran the call (agents/base.py's BaseAgent.model), rather
        # than discarded like it was before this field existed.
        enriched = result.model_copy(update={"model": getattr(self._agent, "model", None)})
        return enriched.model_dump(mode="json")
