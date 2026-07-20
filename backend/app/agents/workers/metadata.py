from app.agents.base import BaseAgent
from app.domain.models.worker_output import WorkerOutput


class MetadataAgent(BaseAgent):
    """docs/agent-architecture.md §1 Worker Agents - title tags, meta
    descriptions, Open Graph/Twitter cards, canonical tags."""

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
