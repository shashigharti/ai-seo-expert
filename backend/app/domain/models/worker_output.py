from pydantic import BaseModel, Field

from app.domain.models.agent_result import Finding, FollowUpSuggestion


class WorkerOutput(BaseModel):
    """What a worker agent's model call must produce - the subset of
    AgentResult that's actually the LLM's job to generate. `task_id` and
    `agent_name` are filled in by BaseAgent.execute(), not the model.
    """

    findings: list[Finding] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    limitations: list[str] = Field(default_factory=list)
    follow_up_suggestions: list[FollowUpSuggestion] = Field(default_factory=list)
