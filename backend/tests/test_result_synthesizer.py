import uuid

from app.application.synthesis.result_synthesizer import synthesize_report
from app.domain.models.agent_result import Finding


def _finding(category: str, severity: str, title: str) -> Finding:
    return Finding(
        category=category,
        severity=severity,
        title=title,
        description="desc",
        evidence="evidence",
        recommendation="fix it",
    )


def test_synthesize_report_aggregates_severity_and_category_counts():
    workflow_id = uuid.uuid4()
    findings = [
        _finding("crawlability", "high", "robots.txt blocks /products"),
        _finding("crawlability", "medium", "sitemap.xml missing entries"),
        _finding("metadata", "high", "Missing meta description"),
    ]

    report = synthesize_report(workflow_id, findings)

    assert report.workflow_id == workflow_id
    assert report.total_findings == 3
    assert report.findings_by_severity == {"high": 2, "medium": 1}
    assert report.findings_by_category == {"crawlability": 2, "metadata": 1}
    assert report.findings == findings


def test_synthesize_report_handles_no_findings():
    report = synthesize_report(uuid.uuid4(), [])
    assert report.total_findings == 0
    assert report.findings_by_severity == {}
    assert report.findings_by_category == {}
    assert report.findings == []
