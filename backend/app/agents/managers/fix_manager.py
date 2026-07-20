import re
from collections import defaultdict
from uuid import uuid4

from app.agents.base import BaseAgent
from app.domain.models.agent_result import AgentResult, Finding
from app.domain.models.fix_outputs import PRDescriptionOutput
from app.domain.models.patch import FixGroup
from app.domain.models.stored_finding import StoredFinding
from app.domain.models.task import Task
from app.domain.models.token_usage import TokenUsage


def _slugify(text: str, max_length: int = 30) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_length] or "fix"


class FixManagerAgent(BaseAgent):
    """docs/agent-architecture.md - SEO Fix Manager: groups approved
    findings, plans PRs (§ Fix Manager: "group approved issues, create fix
    tasks, validate generated changes, prepare pull request plans").

    Grouping itself is deterministic (docs/api-contracts.md's `pr_strategy`
    is a plain string switch - no judgment call needed); the LLM is used
    only for what genuinely benefits from it: drafting a readable PR
    title/body. Like SEOManagerAgent, doesn't implement the generic
    `Agent.execute(task)` shape.
    """

    def __init__(self, name, capability, model_client, tools, skill, model, thinking=False):
        super().__init__(
            name=name,
            capability=capability,
            model_client=model_client,
            tools=tools,
            skill=skill,
            output_model=PRDescriptionOutput,
            model=model,
            thinking=thinking,
        )
        # Set by draft_pr_description after each call - see FixWorkerAgent's
        # last_usage for why this is a side-set attribute rather than a
        # widened return type.
        self.last_usage: TokenUsage | None = None

    def group_approved_findings(
        self, findings: list[StoredFinding], pr_strategy: str
    ) -> list[FixGroup]:
        if pr_strategy == "single":
            if not findings:
                return []
            return [FixGroup(label="all-approved-fixes", finding_ids=[f.id for f in findings])]

        by_category: dict[str, list[StoredFinding]] = defaultdict(list)
        for f in findings:
            by_category[f.finding.category].append(f)
        return [
            FixGroup(label=category, finding_ids=[f.id for f in items])
            for category, items in by_category.items()
        ]

    def branch_name_for(self, group: FixGroup) -> str:
        return f"aiseo/fix-{_slugify(group.label)}-{uuid4().hex[:8]}"

    async def draft_pr_description(self, group: FixGroup, findings: list[Finding]) -> PRDescriptionOutput:
        findings_summary = "\n".join(
            f"- [{f.severity}] {f.title}: {f.recommendation}" for f in findings
        )
        user_prompt = (
            f"Group: {group.label}\n"
            f"Findings being fixed:\n{findings_summary}\n\n"
            "Draft a concise, professional PR title and body summarizing these fixes."
        )
        response = await self.model_client.run(
            system_prompt=self.skill,
            user_prompt=user_prompt,
            output_type=PRDescriptionOutput,
            model=self.model,
            thinking=self.thinking,
        )
        self.last_usage = response.usage
        return response.output

    async def execute(self, task: Task) -> AgentResult:
        raise NotImplementedError(
            "FixManagerAgent groups findings and drafts PR descriptions via "
            "group_approved_findings()/draft_pr_description(); it does not execute individual tasks."
        )
