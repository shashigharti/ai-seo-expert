from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.models.agent_result import Finding


class SEOReport(BaseModel):
    """Unified report produced by the Result Synthesizer
    (docs/architecture.md §7 Main Workflow: "Synthesizer creates unified SEO
    report"). Deterministic aggregation, not itself an LLM call - see
    review/CHANGELOG.md Phase 6 notes for why.
    """

    workflow_id: UUID
    total_findings: int
    findings_by_severity: dict[str, int] = Field(default_factory=dict)
    findings_by_category: dict[str, int] = Field(default_factory=dict)
    findings: list[Finding]
    generated_at: datetime
