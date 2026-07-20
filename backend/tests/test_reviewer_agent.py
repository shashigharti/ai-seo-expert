from app.agents.reviewers.reviewer_agent import CONFIDENCE_REVIEW_THRESHOLD, ReviewerAgent, needs_review
from app.domain.models.agent_result import Finding
from app.domain.models.review_verdict import ReviewVerdict
from app.domain.models.token_usage import TokenUsage
from app.ports.model_client import ModelResponse


class StubModelClient:
    def __init__(self, output: ReviewVerdict):
        self.output = output
        self.calls: list[dict] = []

    async def run(self, system_prompt, user_prompt, output_type, model, thinking=False):
        self.calls.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return ModelResponse(output=self.output, usage=TokenUsage(input_tokens=1, output_tokens=1))


def _finding() -> Finding:
    return Finding(
        category="crawlability",
        severity="medium",
        title="robots.txt blocks /products",
        description="desc",
        evidence="robots.txt line 3: Disallow: /products",
        recommendation="remove the rule",
    )


def test_needs_review_below_threshold():
    assert needs_review(CONFIDENCE_REVIEW_THRESHOLD - 0.01) is True


def test_needs_review_at_or_above_threshold():
    assert needs_review(CONFIDENCE_REVIEW_THRESHOLD) is False
    assert needs_review(0.95) is False


async def test_review_confirms_a_valid_finding():
    finding = _finding()
    verdict = ReviewVerdict(verdict="confirmed", finding=finding, rationale="Evidence is solid.")
    model_client = StubModelClient(verdict)
    reviewer = ReviewerAgent(
        name="ReviewerAgent",
        capability="technical_seo_reviewer",
        model_client=model_client,
        tools={},
        skill="You are a skeptical reviewer.",
        model="qwen-plus",
    )

    result = await reviewer.review(finding, context="Task objective: check crawlability")

    assert result.verdict == "confirmed"
    assert result.finding == finding
    assert finding.title in model_client.calls[0]["user_prompt"]


async def test_review_can_reject_a_finding():
    finding = _finding()
    verdict = ReviewVerdict(verdict="rejected", finding=None, rationale="Evidence doesn't support the claim.")
    reviewer = ReviewerAgent(
        name="ReviewerAgent",
        capability="general_seo_reviewer",
        model_client=StubModelClient(verdict),
        tools={},
        skill="prompt",
        model="qwen-plus",
    )

    result = await reviewer.review(finding, context="ctx")

    assert result.verdict == "rejected"
    assert result.finding is None
