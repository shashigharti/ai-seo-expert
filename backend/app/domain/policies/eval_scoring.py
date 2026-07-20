from app.domain.models.agent_result import Finding
from app.domain.models.eval_case import ExpectedFinding
from app.domain.models.eval_result import OutputScore, TrajectoryScore

# The only place trajectory and output combine into one number - every
# caller (eval_runner.py today, any future reporting/regression-gate tool)
# goes through overall_score() rather than re-deriving a formula, so "how
# good was this run" means the same thing everywhere it's used.
_TRAJECTORY_WEIGHT = 0.4
_OUTPUT_WEIGHT = 0.6


def score_trajectory(planned_capabilities: list[str], expected_capabilities: list[str]) -> TrajectoryScore:
    """Set-based precision/recall/F1 between what the manager actually
    planned and what the golden case says should have been planned - the
    trajectory half of the eval, independent of what any worker then found.
    """
    planned_set = set(planned_capabilities)
    expected_set = set(expected_capabilities)
    matched = sorted(planned_set & expected_set)
    missing = sorted(expected_set - planned_set)
    extra = sorted(planned_set - expected_set)

    precision = len(matched) / len(planned_set) if planned_set else 1.0
    recall = len(matched) / len(expected_set) if expected_set else 1.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)

    return TrajectoryScore(
        planned=sorted(planned_set),
        expected=sorted(expected_set),
        matched=matched,
        missing=missing,
        extra=extra,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def _finding_matches(finding: Finding, expected: ExpectedFinding) -> bool:
    if finding.category != expected.category:
        return False
    haystack = f"{finding.title} {finding.description} {finding.evidence}".lower()
    return expected.keyword.lower() in haystack


def score_output(actual_findings: list[Finding], expected_findings: list[ExpectedFinding]) -> OutputScore:
    """Did the analysis surface the issues a correct run should find.
    Matching is a deterministic category + keyword substring check, not an
    LLM-as-judge call - exact finding wording varies between model runs,
    but a correct finding about a real issue will always mention the term
    that names it (e.g. "description" for a missing meta description).
    A case with no expected findings scores full coverage trivially (there
    was nothing to miss) - such a case is instead testing the trajectory,
    or that the worker doesn't hallucinate findings on a clean repository.
    """
    matched: list[str] = []
    missing: list[str] = []
    for expected in expected_findings:
        label = f"{expected.category}:{expected.keyword}"
        if any(_finding_matches(f, expected) for f in actual_findings):
            matched.append(label)
        else:
            missing.append(label)

    coverage = len(matched) / len(expected_findings) if expected_findings else 1.0
    return OutputScore(matched=matched, missing=missing, coverage=coverage)


def overall_score(trajectory: TrajectoryScore, output: OutputScore) -> float:
    """Single combined number for regression tracking across a SKILL.md or
    model change - the one place "how good was this run" is defined.
    """
    return _TRAJECTORY_WEIGHT * trajectory.f1 + _OUTPUT_WEIGHT * output.coverage
