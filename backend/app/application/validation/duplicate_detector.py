from difflib import SequenceMatcher

from app.domain.models.agent_result import Finding

DEFAULT_SIMILARITY_THRESHOLD = 0.85


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(a=a.lower().strip(), b=b.lower().strip()).ratio()


def _is_duplicate(a: Finding, b: Finding, threshold: float) -> bool:
    if a.category != b.category:
        return False
    return _similarity(a.title, b.title) >= threshold


def deduplicate_findings(
    findings: list[Finding], threshold: float = DEFAULT_SIMILARITY_THRESHOLD
) -> list[Finding]:
    """docs/agent-architecture.md §10 Review Flow, step 3: Duplicate
    Detector. Different workers can flag the same underlying issue (e.g.
    both technical_seo and content_seo notice a missing canonical tag) -
    this collapses near-duplicates (same category, high title similarity)
    down to one, keeping the first occurrence encountered.

    No ML/embedding dependency: title similarity via stdlib `difflib` is
    cheap and good enough for near-duplicate titles from LLM output, which
    tend to be lexically close when they're about the same issue.
    """
    unique: list[Finding] = []
    for finding in findings:
        if not any(_is_duplicate(finding, kept, threshold) for kept in unique):
            unique.append(finding)
    return unique
