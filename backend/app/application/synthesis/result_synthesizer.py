from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from app.domain.models.agent_result import Finding
from app.domain.models.seo_report import SEOReport


def synthesize_report(workflow_id: UUID, findings: list[Finding]) -> SEOReport:
    """docs/architecture.md §7 Main Workflow: "Synthesizer creates unified
    SEO report". Deterministic aggregation, not an LLM call - §1 Agent
    Categories names Manager/Worker/Reviewer as the agent types; "Synthesizer"
    only appears as a workflow step, and grouping/counting already-validated
    findings needs no model call, so this stays a plain, fast, cheap
    function rather than an unnecessary agent.

    Callers are expected to pass findings that have already gone through
    schema validation, evidence validation, deduplication, and review
    (docs/agent-architecture.md §10) - this function only aggregates.
    """
    severity_counts = Counter(f.severity for f in findings)
    category_counts = Counter(f.category for f in findings)

    return SEOReport(
        workflow_id=workflow_id,
        total_findings=len(findings),
        findings_by_severity=dict(severity_counts),
        findings_by_category=dict(category_counts),
        findings=findings,
        generated_at=datetime.now(timezone.utc),
    )
