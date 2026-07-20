import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.repositories.workflow_repository import PostgresWorkflowRepository
from app.application.workflows.analysis_runner import run_seo_analysis
from app.application.workflows.service import WorkflowService
from app.domain.enums.workflow_status import WorkflowStatus
from app.domain.errors import ExternalErrorKind, ExternalServiceError
from tests.conftest import TestingSessionLocal


class _FakeFactory:
    """Stands in for build_agent_factory's real AgentFactory - lets these
    tests drive run_seo_analysis's own status-transition logic (the thing
    under test) without needing a real SEOManagerAgent/Qwen call or its
    exact output schema.
    """

    def __init__(self, manager) -> None:
        self._manager = manager

    def create(self, capability: str):
        assert capability == "seo_manager"
        return self._manager


class _PlanSucceedsManager:
    async def plan(self, workflow, memory_context: str = ""):
        return []


class _PlanFailsManager:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def plan(self, workflow, memory_context: str = ""):
        raise self._exc


@pytest.fixture(autouse=True)
def use_test_session(monkeypatch: pytest.MonkeyPatch):
    """run_seo_analysis opens its own SessionLocal() rather than reusing the
    request's, since a real background task outlives the request that
    spawned it - point that at this test suite's in-memory SQLite engine
    (shared via SQLAlchemy's automatic StaticPool for `:memory:` URLs, so a
    second, separate session still sees data `db_session` already
    committed) instead of the real Postgres from backend/.env.
    """
    monkeypatch.setattr("app.application.workflows.analysis_runner.SessionLocal", TestingSessionLocal)


async def _create_workflow(db_session: AsyncSession):
    return await WorkflowService(PostgresWorkflowRepository(db_session)).create_workflow(
        repository_url="https://github.com/example/project", goal="Audit SEO"
    )


async def test_run_seo_analysis_marks_workflow_completed_on_success(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    workflow = await _create_workflow(db_session)
    monkeypatch.setattr(
        "app.application.workflows.analysis_runner.build_agent_factory",
        lambda model_client: _FakeFactory(_PlanSucceedsManager()),
    )

    await run_seo_analysis(workflow.id)

    updated = await PostgresWorkflowRepository(db_session).get(workflow.id)
    assert updated.status == WorkflowStatus.COMPLETED
    assert updated.error_message is None


async def test_run_seo_analysis_marks_workflow_failed_with_curated_message(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    workflow = await _create_workflow(db_session)
    classified = ExternalServiceError(
        service="Qwen Cloud",
        kind=ExternalErrorKind.AUTH,
        message="Qwen Cloud rejected the configured QWEN_API_KEY.",
    )
    monkeypatch.setattr(
        "app.application.workflows.analysis_runner.build_agent_factory",
        lambda model_client: _FakeFactory(_PlanFailsManager(classified)),
    )

    await run_seo_analysis(workflow.id)

    updated = await PostgresWorkflowRepository(db_session).get(workflow.id)
    assert updated.status == WorkflowStatus.FAILED
    assert updated.error_message == "Qwen Cloud rejected the configured QWEN_API_KEY."


async def test_run_seo_analysis_marks_workflow_failed_with_generic_message_for_unclassified_error(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    workflow = await _create_workflow(db_session)
    monkeypatch.setattr(
        "app.application.workflows.analysis_runner.build_agent_factory",
        lambda model_client: _FakeFactory(_PlanFailsManager(RuntimeError("some internal detail"))),
    )

    await run_seo_analysis(workflow.id)

    updated = await PostgresWorkflowRepository(db_session).get(workflow.id)
    assert updated.status == WorkflowStatus.FAILED
    assert "some internal detail" not in updated.error_message
    assert updated.error_message == "An unexpected error occurred. Check server logs for details."


async def test_run_seo_analysis_does_nothing_for_unknown_workflow():
    # Should log and return quietly rather than raising - there is no
    # workflow row to update either way.
    await run_seo_analysis(uuid.uuid4())
