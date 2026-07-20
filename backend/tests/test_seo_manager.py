import uuid
from datetime import datetime, timezone

import pytest

from app.agents.managers.seo_manager import SEOManagerAgent
from app.domain.enums.workflow_status import WorkflowStatus
from app.domain.models.agent_result import AgentResult, FollowUpSuggestion
from app.domain.models.manager_decision import PlannedCapability, SEOEvaluationOutput, SEOPlanOutput
from app.domain.models.workflow import Workflow
from app.ports.model_client import ModelResponse
from app.domain.models.token_usage import TokenUsage


class StubModelClient:
    """A ModelClient test double that returns a pre-scripted output,
    regardless of prompt content, and records the call for assertions.
    """

    def __init__(self, output):
        self.output = output
        self.calls: list[dict] = []

    async def run(self, system_prompt, user_prompt, output_type, model, thinking=False):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "output_type": output_type,
                "model": model,
                "thinking": thinking,
            }
        )
        return ModelResponse(output=self.output, usage=TokenUsage(input_tokens=10, output_tokens=10))


@pytest.fixture
def workflow() -> Workflow:
    now = datetime.now(timezone.utc)
    return Workflow(
        id=uuid.uuid4(),
        repository_url="https://github.com/example/project",
        branch="feature/pr-42",
        goal="Review this branch for SEO issues",
        status=WorkflowStatus.RUNNING,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture(autouse=True)
def stub_list_repository_files(monkeypatch: pytest.MonkeyPatch):
    """plan() now fetches a real file listing before planning (see
    _repository_files_section) - stub it so existing tests in this file,
    which only care about planning logic, don't make a real network call
    to a nonexistent 'example/project' repo. Tests that care about the
    listing's actual effect on the prompt override this locally.
    """

    async def fake_list_repository_files(repository_url: str, ref: str = "HEAD"):
        return ["index.html", "src/App.jsx"]

    monkeypatch.setattr(
        "app.agents.managers.seo_manager.list_repository_files", fake_list_repository_files
    )


async def test_plan_converts_planned_capabilities_into_task_briefs(workflow: Workflow):
    plan_output = SEOPlanOutput(
        capabilities=[
            PlannedCapability(
                capability="technical_seo",
                objective="Check crawlability",
                acceptance_criteria=["Identify crawl-blocking rules"],
                priority="high",
            ),
            PlannedCapability(capability="metadata", objective="Check meta tags"),
        ],
        rationale="PR touches routing and templates.",
    )
    model_client = StubModelClient(plan_output)
    manager = SEOManagerAgent(
        name="SEOManagerAgent",
        capability="seo_manager",
        model_client=model_client,
        tools=[],
        skill="You are the SEO Review Manager.",
        model="qwen-max",
        thinking=True,
    )

    briefs = await manager.plan(workflow)

    assert len(briefs) == 2
    assert briefs[0].capability == "technical_seo"
    assert briefs[0].workflow_id == workflow.id
    assert briefs[0].expected_output == "TechnicalSEOResult"
    assert briefs[0].priority == "high"
    assert briefs[1].capability == "metadata"
    assert briefs[1].expected_output == "MetadataResult"

    # Every brief gets its own unique id
    assert briefs[0].id != briefs[1].id

    assert model_client.calls[0]["output_type"] is SEOPlanOutput
    assert model_client.calls[0]["thinking"] is True
    assert workflow.goal in model_client.calls[0]["user_prompt"]

    # The real file listing (stubbed by stub_list_repository_files) must
    # reach the prompt - this is the actual fix: scope.files decisions are
    # no longer made with zero visibility into what's really in the repo.
    assert "index.html" in model_client.calls[0]["user_prompt"]
    assert "src/App.jsx" in model_client.calls[0]["user_prompt"]


async def test_plan_falls_back_gracefully_when_file_listing_fails(
    workflow: Workflow, monkeypatch: pytest.MonkeyPatch
):
    async def failing_list_repository_files(repository_url: str, ref: str = "HEAD"):
        raise RuntimeError("simulated listing failure")

    monkeypatch.setattr(
        "app.agents.managers.seo_manager.list_repository_files", failing_list_repository_files
    )

    plan_output = SEOPlanOutput(
        capabilities=[PlannedCapability(capability="technical_seo", objective="Check crawlability")],
        rationale="",
    )
    model_client = StubModelClient(plan_output)
    manager = SEOManagerAgent(
        name="SEOManagerAgent",
        capability="seo_manager",
        model_client=model_client,
        tools=[],
        skill="prompt",
        model="qwen-max",
    )

    # Must not raise - a listing hiccup is not a reason to fail the whole
    # workflow; planning proceeds the same way it always did before this
    # tool existed.
    briefs = await manager.plan(workflow)

    assert len(briefs) == 1
    assert "index.html" not in model_client.calls[0]["user_prompt"]


async def test_plan_with_no_relevant_capabilities_returns_empty_list(workflow: Workflow):
    model_client = StubModelClient(SEOPlanOutput(capabilities=[], rationale="Docs-only change."))
    manager = SEOManagerAgent(
        name="SEOManagerAgent",
        capability="seo_manager",
        model_client=model_client,
        tools=[],
        skill="prompt",
        model="qwen-max",
    )

    briefs = await manager.plan(workflow)

    assert briefs == []


async def test_evaluate_returns_completion_when_model_says_complete(workflow: Workflow):
    evaluation = SEOEvaluationOutput(is_complete=True, rationale="Coverage sufficient.", follow_up_capabilities=[])
    model_client = StubModelClient(evaluation)
    manager = SEOManagerAgent(
        name="SEOManagerAgent",
        capability="seo_manager",
        model_client=model_client,
        tools=[],
        skill="prompt",
        model="qwen-max",
    )
    results = [
        AgentResult(
            task_id=uuid.uuid4(),
            agent_name="TechnicalSEOAgent",
            status="completed",
            findings=[],
            confidence=0.9,
            limitations=[],
            follow_up_suggestions=[],
        )
    ]

    decision = await manager.evaluate(workflow, results)

    assert decision.is_complete is True
    assert decision.follow_up_briefs == []


async def test_evaluate_converts_approved_follow_ups_into_briefs(workflow: Workflow):
    evaluation = SEOEvaluationOutput(
        is_complete=False,
        rationale="Structured data looks incomplete.",
        follow_up_capabilities=[
            PlannedCapability(capability="structured_data", objective="Validate product schema")
        ],
    )
    model_client = StubModelClient(evaluation)
    manager = SEOManagerAgent(
        name="SEOManagerAgent",
        capability="seo_manager",
        model_client=model_client,
        tools=[],
        skill="prompt",
        model="qwen-max",
    )
    results = [
        AgentResult(
            task_id=uuid.uuid4(),
            agent_name="TechnicalSEOAgent",
            status="completed",
            findings=[],
            confidence=0.6,
            limitations=[],
            follow_up_suggestions=[
                FollowUpSuggestion(capability="structured_data", reason="Product schema appears incomplete")
            ],
        )
    ]

    decision = await manager.evaluate(workflow, results)

    assert decision.is_complete is False
    assert len(decision.follow_up_briefs) == 1
    assert decision.follow_up_briefs[0].capability == "structured_data"
    assert decision.follow_up_briefs[0].workflow_id == workflow.id


async def test_execute_is_not_supported_for_the_manager(workflow: Workflow):
    manager = SEOManagerAgent(
        name="SEOManagerAgent",
        capability="seo_manager",
        model_client=StubModelClient(SEOPlanOutput(capabilities=[], rationale="")),
        tools=[],
        skill="prompt",
        model="qwen-max",
    )
    with pytest.raises(NotImplementedError):
        await manager.execute(task=None)  # type: ignore[arg-type]
