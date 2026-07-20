from app.application.validation.evidence_validator import has_sufficient_evidence, partition_by_evidence
from app.domain.models.agent_result import Finding


def _finding(evidence: str) -> Finding:
    return Finding(
        category="crawlability",
        severity="medium",
        title="Some issue",
        description="desc",
        evidence=evidence,
        recommendation="fix it",
    )


def test_has_sufficient_evidence_true_for_substantive_text():
    assert has_sufficient_evidence(_finding("robots.txt line 3: Disallow: /products")) is True


def test_has_sufficient_evidence_false_for_empty_string():
    assert has_sufficient_evidence(_finding("")) is False


def test_has_sufficient_evidence_false_for_whitespace_only():
    assert has_sufficient_evidence(_finding("   ")) is False


def test_has_sufficient_evidence_false_for_short_placeholder_text():
    assert has_sufficient_evidence(_finding("n/a")) is False


def test_partition_by_evidence_splits_correctly():
    good = _finding("robots.txt line 3: Disallow: /products")
    bad = _finding("")
    with_evidence, without_evidence = partition_by_evidence([good, bad])
    assert with_evidence == [good]
    assert without_evidence == [bad]
