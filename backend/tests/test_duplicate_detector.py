from app.application.validation.duplicate_detector import deduplicate_findings
from app.domain.models.agent_result import Finding


def _finding(category: str, title: str) -> Finding:
    return Finding(
        category=category,
        severity="medium",
        title=title,
        description="desc",
        evidence="evidence",
        recommendation="fix it",
    )


def test_deduplicate_keeps_distinct_findings():
    a = _finding("crawlability", "robots.txt blocks /products")
    b = _finding("metadata", "Missing meta description on homepage")
    result = deduplicate_findings([a, b])
    assert result == [a, b]


def test_deduplicate_collapses_near_identical_titles_in_same_category():
    a = _finding("crawlability", "robots.txt blocks /products page")
    b = _finding("crawlability", "robots.txt blocks the /products page")
    result = deduplicate_findings([a, b])
    assert result == [a]


def test_deduplicate_does_not_collapse_same_title_in_different_categories():
    a = _finding("crawlability", "Missing canonical tag")
    b = _finding("metadata", "Missing canonical tag")
    result = deduplicate_findings([a, b])
    assert result == [a, b]


def test_deduplicate_empty_list_returns_empty_list():
    assert deduplicate_findings([]) == []


def test_deduplicate_respects_custom_threshold():
    a = _finding("crawlability", "robots.txt issue")
    b = _finding("crawlability", "sitemap.xml issue")
    # Same category, different enough titles that even a low threshold keeps both
    assert deduplicate_findings([a, b], threshold=0.95) == [a, b]
