from app.domain.models.agent_result import Finding

MIN_EVIDENCE_LENGTH = 10


def has_sufficient_evidence(finding: Finding, min_length: int = MIN_EVIDENCE_LENGTH) -> bool:
    """docs/agent-architecture.md §10 Review Flow, step 2: Evidence
    Validator. Encodes the rule every worker prompt already states ("do not
    report a finding without evidence") as an enforced check, rather than
    trusting the model followed the instruction.
    """
    evidence = finding.evidence.strip()
    return len(evidence) >= min_length


def partition_by_evidence(
    findings: list[Finding], min_length: int = MIN_EVIDENCE_LENGTH
) -> tuple[list[Finding], list[Finding]]:
    """Returns (findings_with_evidence, findings_without_evidence)."""
    with_evidence = [f for f in findings if has_sufficient_evidence(f, min_length)]
    without_evidence = [f for f in findings if not has_sufficient_evidence(f, min_length)]
    return with_evidence, without_evidence
