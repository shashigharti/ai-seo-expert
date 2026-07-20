from app.domain.models.agent_result import Finding
from app.domain.models.eval_case import ExpectedFinding
from app.domain.policies.eval_scoring import overall_score, score_output, score_trajectory


def _finding(category: str, description: str) -> Finding:
    return Finding(
        category=category,
        severity="medium",
        title="A finding",
        description=description,
        evidence="some evidence",
        recommendation="fix it",
    )


def test_score_trajectory_perfect_match():
    score = score_trajectory(["technical_seo", "metadata"], ["technical_seo", "metadata"])

    assert score.matched == ["metadata", "technical_seo"]
    assert score.missing == []
    assert score.extra == []
    assert score.precision == 1.0
    assert score.recall == 1.0
    assert score.f1 == 1.0


def test_score_trajectory_penalizes_missing_capability():
    score = score_trajectory(["technical_seo"], ["technical_seo", "metadata"])

    assert score.missing == ["metadata"]
    assert score.recall == 0.5
    assert score.precision == 1.0


def test_score_trajectory_penalizes_extra_capability():
    score = score_trajectory(["technical_seo", "performance"], ["technical_seo"])

    assert score.extra == ["performance"]
    assert score.precision == 0.5
    assert score.recall == 1.0


def test_score_trajectory_no_capabilities_planned_or_expected_gives_full_score():
    score = score_trajectory([], [])
    assert score.precision == 1.0
    assert score.recall == 1.0
    assert score.f1 == 1.0


def test_score_output_matches_by_category_and_keyword_substring():
    findings = [_finding("metadata", "The page is missing a meta description tag.")]
    expected = [ExpectedFinding(category="metadata", keyword="description")]

    result = score_output(findings, expected)

    assert result.matched == ["metadata:description"]
    assert result.missing == []
    assert result.coverage == 1.0


def test_score_output_does_not_match_across_categories():
    findings = [_finding("accessibility", "Missing a description of the image via alt text.")]
    expected = [ExpectedFinding(category="metadata", keyword="description")]

    result = score_output(findings, expected)

    assert result.matched == []
    assert result.missing == ["metadata:description"]
    assert result.coverage == 0.0


def test_score_output_with_no_expected_findings_is_trivially_full_coverage():
    result = score_output([], [])
    assert result.coverage == 1.0
    assert result.matched == []
    assert result.missing == []


def test_score_output_partial_coverage():
    findings = [_finding("metadata", "Missing meta description.")]
    expected = [
        ExpectedFinding(category="metadata", keyword="description"),
        ExpectedFinding(category="accessibility", keyword="lang"),
    ]

    result = score_output(findings, expected)

    assert result.matched == ["metadata:description"]
    assert result.missing == ["accessibility:lang"]
    assert result.coverage == 0.5


def test_overall_score_combines_trajectory_and_output_with_documented_weights():
    trajectory = score_trajectory(["metadata"], ["metadata", "accessibility"])  # f1 = 2/3
    output = score_output(
        [_finding("metadata", "Missing meta description.")],
        [ExpectedFinding(category="metadata", keyword="description")],
    )  # coverage = 1.0

    score = overall_score(trajectory, output)

    assert score == 0.4 * trajectory.f1 + 0.6 * output.coverage
