import uuid
from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.repositories.task_repository import PostgresTaskRepository
from app.adapters.postgres.repositories.workflow_repository import PostgresWorkflowRepository
from app.domain.enums.task_status import TaskStatus
from app.domain.enums.workflow_status import WorkflowStatus
from app.domain.models.task import Task
from app.domain.models.workflow import Workflow


async def _create_workflow(db_session: AsyncSession) -> Workflow:
    now = datetime.now(timezone.utc)
    workflow = Workflow(
        id=uuid.uuid4(),
        repository_url="https://github.com/example/project",
        branch="master",
        goal="Audit SEO",
        status=WorkflowStatus.RUNNING,
        created_at=now,
        updated_at=now,
    )
    return await PostgresWorkflowRepository(db_session).create(workflow)


async def test_list_tasks_returns_empty_for_a_workflow_with_no_tasks(client: AsyncClient, db_session: AsyncSession):
    workflow = await _create_workflow(db_session)

    response = await client.get(f"/api/workflows/{workflow.id}/tasks")

    assert response.status_code == 200
    assert response.json() == {"items": []}


async def test_list_tasks_enriches_a_completed_task_with_agent_result_fields(
    client: AsyncClient, db_session: AsyncSession
):
    workflow = await _create_workflow(db_session)
    now = datetime.now(timezone.utc)
    task = Task(
        id=uuid.uuid4(),
        workflow_id=workflow.id,
        capability="technical_seo",
        status=TaskStatus.COMPLETED,
        started_at=now,
        created_at=now,
        updated_at=now,
        output={
            "task_id": str(uuid.uuid4()),
            "agent_name": "TechnicalSEOAgent",
            "status": "completed",
            "findings": [],
            "confidence": 0.9,
            "limitations": [],
            "follow_up_suggestions": [],
            "token_usage": {"input_tokens": 100, "output_tokens": 50},
            "model": "qwen-plus",
        },
    )
    await PostgresTaskRepository(db_session).create(task)

    response = await client.get(f"/api/workflows/{workflow.id}/tasks")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["capability"] == "technical_seo"
    assert item["status"] == "completed"
    assert item["agent_name"] == "TechnicalSEOAgent"
    assert item["confidence"] == 0.9
    assert item["model"] == "qwen-plus"
    assert item["token_usage"] == {
        "input_tokens": 100,
        "output_tokens": 50,
        "total_tokens": 150,
        "reasoning_tokens": None,
    }
    assert item["estimated_cost_usd"] is not None
    assert item["reasoning"] is None  # this task's output has no thinking-mode trace


async def test_list_tasks_surfaces_reasoning_trace_and_reasoning_tokens_when_present(
    client: AsyncClient, db_session: AsyncSession
):
    """A thinking-mode agent's reasoning trace + its reasoning_tokens
    breakdown (a subset of output_tokens - see TokenUsage) round-trip
    through the API, distinct from an agent that never used thinking mode
    (the previous test - reasoning/reasoning_tokens both None there)."""
    workflow = await _create_workflow(db_session)
    now = datetime.now(timezone.utc)
    task = Task(
        id=uuid.uuid4(),
        workflow_id=workflow.id,
        capability="accessibility",
        status=TaskStatus.COMPLETED,
        started_at=now,
        created_at=now,
        updated_at=now,
        output={
            "task_id": str(uuid.uuid4()),
            "agent_name": "AccessibilityAgent",
            "status": "completed",
            "findings": [],
            "confidence": 0.9,
            "limitations": [],
            "follow_up_suggestions": [],
            "token_usage": {"input_tokens": 100, "output_tokens": 500, "reasoning_tokens": 380},
            "model": "qwen-plus",
            "reasoning": "First I checked for a <title> element, then reviewed heading structure...",
        },
    )
    await PostgresTaskRepository(db_session).create(task)

    response = await client.get(f"/api/workflows/{workflow.id}/tasks")

    item = response.json()["items"][0]
    assert item["reasoning"] == "First I checked for a <title> element, then reviewed heading structure..."
    assert item["token_usage"]["reasoning_tokens"] == 380


async def test_list_tasks_leaves_enrichment_fields_absent_for_a_pending_task(
    client: AsyncClient, db_session: AsyncSession
):
    workflow = await _create_workflow(db_session)
    now = datetime.now(timezone.utc)
    task = Task(
        id=uuid.uuid4(),
        workflow_id=workflow.id,
        capability="metadata",
        status=TaskStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    await PostgresTaskRepository(db_session).create(task)

    response = await client.get(f"/api/workflows/{workflow.id}/tasks")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["status"] == "pending"
    assert item["agent_name"] is None
    assert item["token_usage"] is None
    assert item["started_at"] is None
