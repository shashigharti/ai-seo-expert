import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.repositories.approval_repository import PostgresApprovalRepository
from app.adapters.postgres.repositories.memory_repository import PostgresMemoryRepository
from app.adapters.postgres.repositories.result_repository import PostgresResultRepository
from app.adapters.postgres.repositories.task_repository import PostgresTaskRepository
from app.adapters.postgres.repositories.workflow_repository import PostgresWorkflowRepository
from app.application.approvals.service import ApprovalService, UnknownFindingIdsError
from app.application.memory.service import MemoryService
from app.application.workflows.service import WorkflowService
from app.domain.enums.finding_status import FindingStatus
from app.domain.enums.task_status import TaskStatus
from app.domain.models.agent_result import Finding
from app.domain.models.stored_finding import StoredFinding


async def _make_workflow_and_task(db_session: AsyncSession):
    workflow = await WorkflowService(PostgresWorkflowRepository(db_session)).create_workflow(
        repository_url="https://github.com/example/project", goal="Audit SEO"
    )
    from app.domain.models.task import Task

    now = datetime.now(timezone.utc)
    task = await PostgresTaskRepository(db_session).create(
        Task(
            id=uuid.uuid4(),
            workflow_id=workflow.id,
            capability="technical_seo",
            status=TaskStatus.COMPLETED,
            created_at=now,
            updated_at=now,
        )
    )
    return workflow, task


def _finding(title: str = "robots.txt blocks /products") -> Finding:
    return Finding(
        category="crawlability",
        severity="high",
        title=title,
        description="desc",
        evidence="robots.txt line 3",
        recommendation="fix it",
    )


@pytest.fixture
def service(db_session: AsyncSession) -> ApprovalService:
    return ApprovalService(
        PostgresResultRepository(db_session),
        PostgresApprovalRepository(db_session),
        PostgresWorkflowRepository(db_session),
        MemoryService(PostgresMemoryRepository(db_session)),
    )


async def test_list_findings_returns_persisted_findings(db_session: AsyncSession, service: ApprovalService):
    workflow, task = await _make_workflow_and_task(db_session)
    stored = StoredFinding(
        id=uuid.uuid4(),
        workflow_id=workflow.id,
        task_id=task.id,
        agent_name="TechnicalSEOAgent",
        finding=_finding(),
        created_at=datetime.now(timezone.utc),
    )
    await PostgresResultRepository(db_session).save_many([stored])

    findings = await service.list_findings(workflow.id)

    assert len(findings) == 1
    assert findings[0].finding.title == "robots.txt blocks /products"
    assert findings[0].status == FindingStatus.PENDING


async def test_approve_marks_findings_approved_and_records_audit_trail(
    db_session: AsyncSession, service: ApprovalService
):
    workflow, task = await _make_workflow_and_task(db_session)
    stored = StoredFinding(
        id=uuid.uuid4(),
        workflow_id=workflow.id,
        task_id=task.id,
        agent_name="TechnicalSEOAgent",
        finding=_finding(),
        created_at=datetime.now(timezone.utc),
    )
    [saved] = await PostgresResultRepository(db_session).save_many([stored])

    approval = await service.approve(workflow.id, [saved.id], pr_strategy="by_category")

    assert approval.workflow_id == workflow.id
    assert approval.finding_ids == [saved.id]
    assert approval.pr_strategy == "by_category"

    findings = await service.list_findings(workflow.id)
    assert findings[0].status == FindingStatus.APPROVED


async def test_approve_raises_for_unknown_finding_id(db_session: AsyncSession, service: ApprovalService):
    workflow, _task = await _make_workflow_and_task(db_session)

    with pytest.raises(UnknownFindingIdsError):
        await service.approve(workflow.id, [uuid.uuid4()], pr_strategy="by_category")
