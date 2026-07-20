from app.agents.base import BaseAgent
from app.domain.models.agent_result import Finding
from app.domain.models.review_verdict import ReviewVerdict


class ReviewerAgent(BaseAgent):
    """docs/agent-architecture.md §1 Reviewer Agents (Technical SEO
    Reviewer, Content Reviewer, General SEO Reviewer) and §10 Review Flow:
    invoked "when needed" - see `needs_review()` - to confirm, adjust, or
    reject a single Finding before it reaches the Manager's decision.

    One shared class backs all three reviewer registrations in
    config/agents.yaml; they differ only by skill (domain focus), which is
    exactly what composition over inheritance (§4) calls for - three near-
    empty subclasses would add nothing workers' pattern didn't already
    justify by potential future divergence.
    """

    def __init__(self, name, capability, model_client, tools, skill, model, thinking=False):
        super().__init__(
            name=name,
            capability=capability,
            model_client=model_client,
            tools=tools,
            skill=skill,
            output_model=ReviewVerdict,
            model=model,
            thinking=thinking,
        )

    async def review(self, finding: Finding, context: str) -> ReviewVerdict:
        user_prompt = (
            f"Context: {context}\n\n"
            f"Finding to review:\n"
            f"- Category: {finding.category}\n"
            f"- Severity: {finding.severity}\n"
            f"- Title: {finding.title}\n"
            f"- Description: {finding.description}\n"
            f"- Evidence: {finding.evidence}\n"
            f"- Recommendation: {finding.recommendation}\n\n"
            "Confirm this finding as-is, adjust it if something is inaccurate "
            "or overstated, or reject it if the evidence doesn't actually "
            "support it."
        )
        response = await self.model_client.run(
            system_prompt=self.skill,
            user_prompt=user_prompt,
            output_type=ReviewVerdict,
            model=self.model,
            thinking=self.thinking,
        )
        return response.output


CONFIDENCE_REVIEW_THRESHOLD = 0.6


def needs_review(finding_confidence: float) -> bool:
    """docs/agent-architecture.md §10: "Reviewer Agent when needed" - needed
    when the worker itself wasn't confident. High-confidence findings skip
    review entirely (cost/latency control, not every finding needs a second
    LLM call).
    """
    return finding_confidence < CONFIDENCE_REVIEW_THRESHOLD
