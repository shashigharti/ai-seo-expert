import uuid
from datetime import datetime, timezone

from app.agents.managers.fix_manager import FixManagerAgent
from app.domain.enums.finding_status import FindingStatus
from app.domain.models.agent_result import Finding
from app.domain.models.fix_outputs import PRDescriptionOutput
from app.domain.models.stored_finding import StoredFinding
from app.domain.models.token_usage import TokenUsage
from app.ports.model_client import ModelResponse


class StubModelClient:
    def __init__(self, output: PRDescriptionOutput):
        self.output = output
        self.calls: list[dict] = []

    async def run(self, system_prompt, user_prompt, output_type, model, thinking=False):
        self.calls.append({"user_prompt": user_prompt})
        return ModelResponse(output=self.output, usage=TokenUsage(input_tokens=1, output_tokens=1))


def _stored_finding(category: str, title: str) -> StoredFinding:
    return StoredFinding(
        id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        agent_name="TechnicalSEOAgent",
        finding=Finding(
            category=category,
            severity="high",
            title=title,
            description="desc",
            evidence="evidence",
            recommendation="fix it",
        ),
        status=FindingStatus.APPROVED,
        created_at=datetime.now(timezone.utc),
    )


def _manager(output=None) -> FixManagerAgent:
    return FixManagerAgent(
        name="FixManagerAgent",
        capability="fix_manager",
        model_client=StubModelClient(output or PRDescriptionOutput(title="Fix SEO issues", body="body")),
        tools={},
        skill="prompt",
        model="qwen-plus",
    )


def test_group_by_category_groups_findings_by_their_category():
    manager = _manager()
    a = _stored_finding("crawlability", "robots.txt issue")
    b = _stored_finding("crawlability", "sitemap issue")
    c = _stored_finding("metadata", "meta description issue")

    groups = manager.group_approved_findings([a, b, c], pr_strategy="by_category")

    groups_by_label = {g.label: set(g.finding_ids) for g in groups}
    assert groups_by_label == {
        "crawlability": {a.id, b.id},
        "metadata": {c.id},
    }


def test_group_single_puts_everything_in_one_group():
    manager = _manager()
    a = _stored_finding("crawlability", "robots.txt issue")
    b = _stored_finding("metadata", "meta description issue")

    groups = manager.group_approved_findings([a, b], pr_strategy="single")

    assert len(groups) == 1
    assert set(groups[0].finding_ids) == {a.id, b.id}


def test_group_single_with_no_findings_returns_no_groups():
    manager = _manager()
    assert manager.group_approved_findings([], pr_strategy="single") == []


def test_branch_name_is_slug_plus_unique_suffix():
    manager = _manager()
    a = _stored_finding("Crawlability & Indexing", "x")
    [group] = manager.group_approved_findings([a], pr_strategy="by_category")

    branch = manager.branch_name_for(group)

    assert branch.startswith("aiseo/fix-crawlability-indexing-")
    # Two calls produce different branch names (unique suffix)
    assert manager.branch_name_for(group) != branch


async def test_draft_pr_description_calls_model_with_findings_context():
    output = PRDescriptionOutput(title="Fix crawlability issues", body="This PR fixes...")
    manager = _manager(output)
    a = _stored_finding("crawlability", "robots.txt blocks /products")
    [group] = manager.group_approved_findings([a], pr_strategy="by_category")

    result = await manager.draft_pr_description(group, [a.finding])

    assert result.title == "Fix crawlability issues"
    assert "robots.txt blocks /products" in manager.model_client.calls[0]["user_prompt"]
