from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.models.token_usage import TokenUsage


class FollowUpSuggestion(BaseModel):
    """docs/agent-architecture.md §7 - workers may suggest, only managers create tasks."""

    capability: str
    reason: str


class Finding(BaseModel):
    """docs/agent-architecture.md §9.

    references/confidence are additions beyond the doc's base schema:
    docs/specs.md §2 requires a per-issue confidence score and links to
    authoritative sources (Google Search Central, MDN, W3C, OWASP, etc.)
    "directly corresponding to the detected issue whenever possible" -
    both optional/default-empty since not every finding will have one.
    """

    category: str
    severity: Literal["low", "medium", "high", "critical"]
    title: str
    description: str
    evidence: str
    recommendation: str
    references: list[str] = Field(default_factory=list)
    confidence: float | None = None


class AgentResult(BaseModel):
    """docs/agent-architecture.md §9.

    task_id is typed UUID here (not str, as the doc's illustrative snippet
    shows) to match this project's Task domain model - see Agents.md General
    Principles "Maintain strong typing where applicable".

    token_usage is an addition beyond the doc's base schema: docs/specs.md
    §"Cost Transparency" requires tokens consumed per agent/issue to be
    shown to the user, and ModelClient.run() already computes this per call
    (Phase 3) - it was being computed and discarded until Phase 10 wired it
    through, which this field closes.

    model is a further addition: the Agent Execution Panel (docs/specs.md
    §4) needs to show which model ran each agent. The model name was
    previously used to make the ModelClient.run() call and then discarded -
    never persisted anywhere, not even internally. Populated in
    AgentTaskExecutorAdapter.execute(), not BaseAgent itself, so it applies
    uniformly regardless of which concrete agent produced the result.
    """

    task_id: UUID
    agent_name: str
    status: Literal["completed", "partial", "failed"]
    findings: list[Finding]
    confidence: float
    limitations: list[str]
    follow_up_suggestions: list[FollowUpSuggestion]
    token_usage: TokenUsage | None = None
    model: str | None = None
    # The model's thinking-mode reasoning trace (docs/specs.md's
    # "expandable sections for advanced details" - the Agent Execution
    # Panel's intermediate-steps disclosure). None for agents that don't
    # use thinking mode (see model_policies' "thinking" flag) - there's no
    # trace to show, not a placeholder for one.
    reasoning: str | None = None
