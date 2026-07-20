from typing import Literal

from pydantic import BaseModel

from app.domain.models.agent_result import Finding


class ReviewVerdict(BaseModel):
    """Output of a Reviewer Agent's assessment of one Finding
    (docs/agent-architecture.md §10 Review Flow: "Reviewer Agent when
    needed" -> "Manager Decision").
    """

    verdict: Literal["confirmed", "adjusted", "rejected"]
    finding: Finding | None
    rationale: str
