import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.events.sse_publisher import SSEEventPublisher
from app.adapters.postgres.repositories.pull_request_repository import PostgresPullRequestRepository
from app.adapters.postgres.repositories.result_repository import PostgresResultRepository
from app.adapters.postgres.repositories.task_repository import PostgresTaskRepository
from app.adapters.postgres.repositories.workflow_repository import PostgresWorkflowRepository
from app.agents.bootstrap import build_agent_factory
from app.application.pull_requests.service import (
    CAPABILITY_PREFIX,
    NoApprovedFindingsError,
    PullRequestService,
    WorkflowNotFoundForPullRequestError,
)
from app.application.workflows.pull_request_runner import run_pull_request_generation
from app.application.workflows.service import WorkflowService
from app.domain.enums.finding_status import FindingStatus
from app.domain.enums.task_status import TaskStatus
from app.domain.errors import ExternalErrorKind, ExternalServiceError
from app.domain.models.agent_result import Finding
from app.domain.models.fix_outputs import PRDescriptionOutput, ProposedPatchOutput
from app.domain.models.patch import ProposedPatch
from app.domain.models.stored_finding import StoredFinding
from app.domain.models.task import Task
from app.domain.models.token_usage import TokenUsage
from app.ports.model_client import ModelResponse
from tests.conftest import TestingSessionLocal


class StubModelClient:
    """Returns a canned response shaped to whatever output_type is asked
    for - good enough for fix_manager's PRDescriptionOutput and fix_worker's
    ProposedPatchOutput calls in the same flow.
    """

    async def run(self, system_prompt, user_prompt, output_type, model, thinking=False):
        if output_type is PRDescriptionOutput:
            output = PRDescriptionOutput(title="Fix crawlability issues", body="This PR fixes...")
        elif output_type is ProposedPatchOutput:
            output = ProposedPatchOutput(new_content="User-agent: *\nAllow: /", commit_message="fix: robots.txt")
        else:
            raise AssertionError(f"Unexpected output_type: {output_type}")
        return ModelResponse(output=output, usage=TokenUsage(input_tokens=1, output_tokens=1))


class StubGitProvider:
    def __init__(self) -> None:
        self.opened_prs: list[dict] = []

    async def get_default_branch(self, repository_url: str) -> str:
        return "main"

    async def open_pull_request(
        self,
        repository_url: str,
        base_branch: str,
        new_branch: str,
        patches: list[ProposedPatch],
        pr_title: str,
        pr_body: str,
    ) -> str:
        self.opened_prs.append(
            {"repository_url": repository_url, "branch": new_branch, "patches": patches, "title": pr_title}
        )
        return f"https://github.com/example/project/pull/{len(self.opened_prs)}"


class FailingGitProvider:
    async def get_default_branch(self, repository_url: str) -> str:
        return "main"

    async def open_pull_request(self, *args, **kwargs) -> str:
        raise RuntimeError("network error")


class ClassifiedFailingGitProvider:
    """Fails with the same classified ExternalServiceError shape a real
    adapter (GitHubProvider, QwenCloudModelClient) raises."""

    async def get_default_branch(self, repository_url: str) -> str:
        return "main"

    async def open_pull_request(self, *args, **kwargs) -> str:
        raise ExternalServiceError(
            service="GitHub", kind=ExternalErrorKind.AUTH, message="GitHub rejected the configured token."
        )


async def _seed_approved_finding(db_session: AsyncSession, workflow_id: uuid.UUID, category: str) -> StoredFinding:
    now = datetime.now(timezone.utc)
    task = await PostgresTaskRepository(db_session).create(
        Task(
            id=uuid.uuid4(),
            workflow_id=workflow_id,
            capability="technical_seo",
            status=TaskStatus.COMPLETED,
            input={"scope": {"files": ["robots.txt"]}, "ref": "HEAD"},
            created_at=now,
            updated_at=now,
        )
    )
    [stored] = await PostgresResultRepository(db_session).save_many(
        [
            StoredFinding(
                id=uuid.uuid4(),
                workflow_id=workflow_id,
                task_id=task.id,
                agent_name="TechnicalSEOAgent",
                finding=Finding(
                    category=category,
                    severity="high",
                    title="robots.txt blocks /products",
                    description="desc",
                    evidence="robots.txt line 3",
                    recommendation="fix it",
                ),
                status=FindingStatus.APPROVED,
                created_at=now,
            )
        ]
    )
    return stored


@pytest.fixture(autouse=True)
def stub_github_file_reader(monkeypatch: pytest.MonkeyPatch):
    """Avoid a real network call to a nonexistent 'example/project' repo -
    matches the mocking pattern used for external calls throughout this
    suite. read_repository_file is called from PullRequestGroupExecutor now
    (moved out of service.py when generation became async/task-based).
    """

    async def fake_read_repository_file(repository_url: str, path: str, ref: str = "HEAD"):
        return "User-agent: *\nDisallow: /products"

    monkeypatch.setattr(
        "app.application.pull_requests.group_executor.read_repository_file", fake_read_repository_file
    )


@pytest.fixture(autouse=True)
def use_test_session(monkeypatch: pytest.MonkeyPatch):
    """run_pull_request_generation opens its own SessionLocal() (background-
    task pattern, same as run_seo_analysis) - point that at this test
    suite's in-memory SQLite engine instead of the real Postgres from
    backend/.env. See test_analysis_runner.py's identical fixture.
    """
    monkeypatch.setattr("app.application.workflows.pull_request_runner.SessionLocal", TestingSessionLocal)


@pytest.fixture
def git_provider() -> StubGitProvider:
    return StubGitProvider()


@pytest.fixture(autouse=True)
def stub_runner_agent_factory(monkeypatch: pytest.MonkeyPatch):
    """run_pull_request_generation builds its own AgentFactory from a real
    QwenCloudModelClient - replace it with one backed by StubModelClient so
    these tests don't need a real QWEN_API_KEY, mirroring
    test_analysis_runner.py's _FakeFactory technique.
    """
    monkeypatch.setattr(
        "app.application.workflows.pull_request_runner.build_agent_factory",
        lambda model_client: build_agent_factory(StubModelClient()),
    )


@pytest.fixture
def stub_runner_git_provider(monkeypatch: pytest.MonkeyPatch, git_provider: StubGitProvider):
    """run_pull_request_generation constructs its own GitHubProvider -
    replace the class with one that returns the test's git_provider stub."""
    monkeypatch.setattr(
        "app.application.workflows.pull_request_runner.GitHubProvider", lambda token: git_provider
    )
    return git_provider


@pytest.fixture
def service(db_session: AsyncSession) -> PullRequestService:
    factory = build_agent_factory(StubModelClient())
    return PullRequestService(
        workflow_repository=PostgresWorkflowRepository(db_session),
        task_repository=PostgresTaskRepository(db_session),
        result_repository=PostgresResultRepository(db_session),
        agent_factory=factory,
        event_publisher=SSEEventPublisher(),
    )


async def test_start_generation_creates_one_pending_task_per_category(
    db_session: AsyncSession, service: PullRequestService
):
    workflow = await WorkflowService(PostgresWorkflowRepository(db_session)).create_workflow(
        repository_url="https://github.com/example/project", goal="Audit SEO"
    )
    stored = await _seed_approved_finding(db_session, workflow.id, category="crawlability")

    tasks = await service.start_generation(workflow.id, pr_strategy="by_category")

    assert len(tasks) == 1
    [task] = tasks
    assert task.status == TaskStatus.PENDING
    assert task.capability.startswith(CAPABILITY_PREFIX)
    assert task.capability == f"{CAPABILITY_PREFIX}crawlability"
    assert task.input["group_label"] == "crawlability"
    assert task.input["finding_ids"] == [str(stored.id)]
    assert task.input["pr_strategy"] == "by_category"


async def test_start_generation_raises_for_unknown_workflow(service: PullRequestService):
    with pytest.raises(WorkflowNotFoundForPullRequestError):
        await service.start_generation(uuid.uuid4(), pr_strategy="by_category")


async def test_start_generation_raises_when_nothing_approved(
    db_session: AsyncSession, service: PullRequestService
):
    workflow = await WorkflowService(PostgresWorkflowRepository(db_session)).create_workflow(
        repository_url="https://github.com/example/project", goal="Audit SEO"
    )
    with pytest.raises(NoApprovedFindingsError):
        await service.start_generation(workflow.id, pr_strategy="by_category")


async def test_run_pull_request_generation_opens_pr_and_persists_result(
    db_session: AsyncSession,
    service: PullRequestService,
    stub_runner_git_provider: StubGitProvider,
):
    workflow = await WorkflowService(PostgresWorkflowRepository(db_session)).create_workflow(
        repository_url="https://github.com/example/project", goal="Audit SEO"
    )
    await _seed_approved_finding(db_session, workflow.id, category="crawlability")
    tasks = await service.start_generation(workflow.id, pr_strategy="by_category")

    await run_pull_request_generation(workflow.id, tasks)

    completed_task = await PostgresTaskRepository(db_session).get(tasks[0].id)
    assert completed_task.status == TaskStatus.COMPLETED
    assert completed_task.output["status"] == "opened"
    assert completed_task.output["token_usage"]["total_tokens"] > 0

    [result] = await PostgresPullRequestRepository(db_session).list_for_workflow(workflow.id)
    assert result.status == "opened"
    assert result.url == "https://github.com/example/project/pull/1"
    assert len(stub_runner_git_provider.opened_prs) == 1
    assert stub_runner_git_provider.opened_prs[0]["patches"][0].file_path == "robots.txt"


async def test_run_pull_request_generation_records_curated_message_on_failure(
    db_session: AsyncSession, service: PullRequestService, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        "app.application.workflows.pull_request_runner.GitHubProvider",
        lambda token: ClassifiedFailingGitProvider(),
    )
    workflow = await WorkflowService(PostgresWorkflowRepository(db_session)).create_workflow(
        repository_url="https://github.com/example/project", goal="Audit SEO"
    )
    await _seed_approved_finding(db_session, workflow.id, category="crawlability")
    tasks = await service.start_generation(workflow.id, pr_strategy="by_category")
    # max_attempts=1 so the Orchestrator's retry/backoff loop doesn't
    # actually sleep between attempts in this test - the retry loop itself
    # is already covered by test_orchestrator.py.
    task_repository = PostgresTaskRepository(db_session)
    tasks[0] = await task_repository.update(tasks[0].model_copy(update={"max_attempts": 1}))

    await run_pull_request_generation(workflow.id, tasks)

    failed_task = await task_repository.get(tasks[0].id)
    assert failed_task.status == TaskStatus.FAILED
    assert failed_task.error_message == "GitHub rejected the configured token."

    [result] = await PostgresPullRequestRepository(db_session).list_for_workflow(workflow.id)
    assert result.status == "failed"
    assert result.url is None
    assert result.error_message == "GitHub rejected the configured token."


async def test_run_pull_request_generation_curates_unclassified_errors(
    db_session: AsyncSession, service: PullRequestService, monkeypatch: pytest.MonkeyPatch
):
    """An unclassified exception (a plain RuntimeError, standing in for any
    bug/failure type this service doesn't specifically know about) must
    never leak its raw text into error_message.
    """
    monkeypatch.setattr(
        "app.application.workflows.pull_request_runner.GitHubProvider", lambda token: FailingGitProvider()
    )
    workflow = await WorkflowService(PostgresWorkflowRepository(db_session)).create_workflow(
        repository_url="https://github.com/example/project", goal="Audit SEO"
    )
    await _seed_approved_finding(db_session, workflow.id, category="crawlability")
    tasks = await service.start_generation(workflow.id, pr_strategy="by_category")
    task_repository = PostgresTaskRepository(db_session)
    tasks[0] = await task_repository.update(tasks[0].model_copy(update={"max_attempts": 1}))

    await run_pull_request_generation(workflow.id, tasks)

    [result] = await PostgresPullRequestRepository(db_session).list_for_workflow(workflow.id)
    assert result.status == "failed"
    assert "network error" not in result.error_message
    assert result.error_message == "An unexpected error occurred. Check server logs for details."
