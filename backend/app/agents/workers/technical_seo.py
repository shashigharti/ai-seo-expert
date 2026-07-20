from app.agents.base import BaseAgent
from app.domain.models.worker_output import WorkerOutput


class TechnicalSEOAgent(BaseAgent):
    """docs/agent-architecture.md §1 Worker Agents - crawlability, indexing,
    robots/sitemap/canonicalization issues. Uses BaseAgent's default
    execute(); this class exists to give the capability a distinct,
    registry-addressable identity (config/agents.yaml `class:`).
    """

    def __init__(self, name, capability, model_client, tools, skill, model, thinking=False):
        super().__init__(
            name=name,
            capability=capability,
            model_client=model_client,
            tools=tools,
            skill=skill,
            output_model=WorkerOutput,
            model=model,
            thinking=thinking,
        )
