import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.repositories.result_repository import PostgresResultRepository
from app.adapters.postgres.repositories.task_repository import PostgresTaskRepository
from app.domain.enums.finding_status import FindingStatus
from app.domain.enums.task_status import TaskStatus
from app.domain.models.agent_result import Finding
from app.domain.models.patch import ProposedPatch
from app.domain.models.stored_finding import StoredFinding
from app.domain.models.task import Task
from app.main import create_app
from tests.conftest import TestingSessionLocal


class StubGitProvider:
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
        return "https://github.com/example/project/pull/1"


@pytest.fixture(autouse=True)
def stub_github_file_reader(monkeypatch: pytest.MonkeyPatch):
    async def fake_read_repository_file(repository_url: str, path: str, ref: str = "HEAD"):
        return "User-agent: *\nDisallow: /products"

    monkeypatch.setattr(
        "app.application.pull_requests.group_executor.read_repository_file", fake_read_repository_file
    )


@pytest.fixture(autouse=True)
def stub_qwen_model_client(monkeypatch: pytest.MonkeyPatch):
    """The route test suite's `client` fixture builds a real app via
    create_app(), whose PullRequestServiceDep constructs a real
    QwenCloudModelClient. Patch PydanticAIAgent so fix_manager/fix_worker
    calls succeed without a real QWEN_API_KEY, same technique as
    test_qwen_model_client.py.
    """
    from unittest.mock import AsyncMock, MagicMock

    from app.domain.models.fix_outputs import PRDescriptionOutput, ProposedPatchOutput

    def make_result(output_type):
        # model_client.py wraps the requested type in NativeOutput before
        # handing it to PydanticAIAgent (see its comment on why) - unwrap
        # it here to see the actual type being requested.
        actual_type = getattr(output_type, "outputs", output_type)
        if actual_type is PRDescriptionOutput:
            output = PRDescriptionOutput(title="Fix issues", body="body")
        else:
            output = ProposedPatchOutput(new_content="fixed", commit_message="fix")
        return MagicMock(output=output, usage=MagicMock(input_tokens=1, output_tokens=1, reasoning_tokens=None))

    def fake_agent_constructor(model, output_type=None, system_prompt=None, **kwargs):
        agent = MagicMock()
        agent.run = AsyncMock(side_effect=lambda *a, **k: make_result(output_type))
        return agent

    monkeypatch.setattr("app.adapters.qwen.model_client.PydanticAIAgent", fake_agent_constructor)
    monkeypatch.setattr("app.adapters.qwen.model_client.OpenAIProvider", MagicMock())
    monkeypatch.setattr("app.adapters.qwen.model_client.OpenAIChatModel", MagicMock())


@pytest.fixture(autouse=True)
def use_test_session_for_runner(monkeypatch: pytest.MonkeyPatch):
    """run_pull_request_generation (kicked off via BackgroundTasks by the
    POST route below) opens its own SessionLocal() - point it at the same
    in-memory SQLite engine `db_session`/the request's overridden get_db use,
    same reasoning as test_analysis_runner.py's identical fixture.
    """
    monkeypatch.setattr("app.application.workflows.pull_request_runner.SessionLocal", TestingSessionLocal)


@pytest.fixture
async def client(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    from httpx import ASGITransport

    from app.adapters.postgres.database import get_db
    from app.api.dependencies import get_git_provider
    from app.config.settings import settings

    # monkeypatch (not a raw assignment) so this reverts automatically -
    # `settings` is a module-level singleton shared across the whole test
    # session; a raw mutation here would leak into every test that runs
    # afterward, including the background run_seo_analysis task attempting
    # a real network call to Qwen Cloud with this fake key.
    monkeypatch.setattr(settings, "qwen_api_key", "test-key")
    # run_pull_request_generation constructs its own GitHubProvider (it's a
    # background task, detached from this request's dependency-injected
    # one) - patch the class it imports directly instead.
    monkeypatch.setattr("app.application.workflows.pull_request_runner.GitHubProvider", lambda token: StubGitProvider())

    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_git_provider] = lambda: StubGitProvider()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/auth/register", json={"email": "test@example.com", "password": "testpass123"})
        token_response = await ac.post(
            "/api/auth/token", data={"username": "test@example.com", "password": "testpass123"}
        )
        token = token_response.json()["access_token"]
        ac.headers.update({"Authorization": f"Bearer {token}"})
        yield ac


async def _seed_approved_finding(db_session: AsyncSession, workflow_id: str) -> None:
    now = datetime.now(timezone.utc)
    task = await PostgresTaskRepository(db_session).create(
        Task(
            id=uuid.uuid4(),
            workflow_id=uuid.UUID(workflow_id),
            capability="technical_seo",
            status=TaskStatus.COMPLETED,
            input={"scope": {"files": ["robots.txt"]}, "ref": "HEAD"},
            created_at=now,
            updated_at=now,
        )
    )
    await PostgresResultRepository(db_session).save_many(
        [
            StoredFinding(
                id=uuid.uuid4(),
                workflow_id=uuid.UUID(workflow_id),
                task_id=task.id,
                agent_name="TechnicalSEOAgent",
                finding=Finding(
                    category="crawlability",
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


async def _await_background_tasks() -> None:
    """FastAPI's TestClient/AsyncClient runs BackgroundTasks after the
    response is sent, on the same event loop - yielding control lets the
    scheduled run_pull_request_generation coroutine actually run to
    completion before assertions below read its effects.
    """
    await asyncio.sleep(0.1)


async def test_generate_pull_requests_returns_202_with_pending_tasks(
    client: AsyncClient, db_session: AsyncSession
):
    create_response = await client.post(
        "/api/workflows", json={"repository_url": "https://github.com/example/project", "goal": "Audit SEO"}
    )
    workflow_id = create_response.json()["id"]
    await _seed_approved_finding(db_session, workflow_id)

    response = await client.post(f"/api/workflows/{workflow_id}/pull-requests", json={"pr_strategy": "by_category"})

    assert response.status_code == 202
    body = response.json()
    assert len(body["task_ids"]) == 1

    await _await_background_tasks()

    list_response = await client.get(f"/api/workflows/{workflow_id}/pull-requests")
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "opened"
    assert items[0]["url"] == "https://github.com/example/project/pull/1"


async def test_pull_request_generation_tasks_appear_in_task_list_with_pull_request_capability(
    client: AsyncClient, db_session: AsyncSession
):
    create_response = await client.post(
        "/api/workflows", json={"repository_url": "https://github.com/example/project", "goal": "Audit SEO"}
    )
    workflow_id = create_response.json()["id"]
    await _seed_approved_finding(db_session, workflow_id)

    await client.post(f"/api/workflows/{workflow_id}/pull-requests", json={"pr_strategy": "by_category"})
    await _await_background_tasks()

    tasks_response = await client.get(f"/api/workflows/{workflow_id}/tasks")
    pr_tasks = [t for t in tasks_response.json()["items"] if t["capability"].startswith("pull_request_")]
    assert len(pr_tasks) == 1
    assert pr_tasks[0]["status"] == "completed"


async def test_generate_pull_requests_no_approved_findings_returns_400(client: AsyncClient):
    create_response = await client.post(
        "/api/workflows", json={"repository_url": "https://github.com/example/project", "goal": "Audit SEO"}
    )
    workflow_id = create_response.json()["id"]

    response = await client.post(f"/api/workflows/{workflow_id}/pull-requests", json={"pr_strategy": "by_category"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NO_APPROVED_FINDINGS"


async def test_generate_pull_requests_unknown_workflow_returns_404(client: AsyncClient):
    response = await client.post(
        f"/api/workflows/{uuid.uuid4()}/pull-requests", json={"pr_strategy": "by_category"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "WORKFLOW_NOT_FOUND"


async def test_list_pull_requests_empty_when_none_generated_yet(client: AsyncClient):
    create_response = await client.post(
        "/api/workflows", json={"repository_url": "https://github.com/example/project", "goal": "Audit SEO"}
    )
    workflow_id = create_response.json()["id"]

    response = await client.get(f"/api/workflows/{workflow_id}/pull-requests")

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_generate_pull_requests_qwen_failure_during_drafting_is_recorded_not_raised(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """fix_manager.draft_pr_description (a real Qwen call) failing must
    still surface as a failed PullRequestResult with a curated
    error_message, not an unhandled exception escaping the background task.
    """
    from unittest.mock import AsyncMock

    from app.domain.errors import ExternalErrorKind, ExternalServiceError

    async def raise_classified(*args, **kwargs):
        raise ExternalServiceError(
            service="Qwen Cloud", kind=ExternalErrorKind.AUTH, message="Qwen Cloud rejected the API key."
        )

    monkeypatch.setattr(
        "app.adapters.qwen.model_client.QwenCloudModelClient.run", AsyncMock(side_effect=raise_classified)
    )

    create_response = await client.post(
        "/api/workflows", json={"repository_url": "https://github.com/example/project", "goal": "Audit SEO"}
    )
    workflow_id = create_response.json()["id"]
    await _seed_approved_finding(db_session, workflow_id)

    response = await client.post(f"/api/workflows/{workflow_id}/pull-requests", json={"pr_strategy": "by_category"})
    assert response.status_code == 202

    # Every retry attempt also hits the classified failure - with the
    # default max_attempts=3, that's real backoff sleeps (~1s + ~2s) before
    # the task settles FAILED; wait long enough for the whole retry loop.
    await asyncio.sleep(4)

    list_response = await client.get(f"/api/workflows/{workflow_id}/pull-requests")
    items = list_response.json()["items"]
    assert items[0]["status"] == "failed"
    assert items[0]["error_message"] == "Qwen Cloud rejected the API key."
