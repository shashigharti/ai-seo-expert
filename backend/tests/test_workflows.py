import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.repositories.workflow_repository import PostgresWorkflowRepository
from app.application.workflows.service import WorkflowService
from app.domain.enums.workflow_status import WorkflowStatus


async def test_create_workflow_via_api(client: AsyncClient):
    response = await client.post(
        "/api/workflows",
        json={
            "repository_url": "https://github.com/example/project",
            "branch": "feature/pr-42",
            "goal": "Review this branch for SEO issues",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == WorkflowStatus.PENDING.value
    assert body["branch"] == "feature/pr-42"
    assert "id" in body


async def test_create_workflow_defaults_branch_to_master(client: AsyncClient):
    response = await client.post(
        "/api/workflows",
        json={"repository_url": "https://github.com/example/project", "goal": "Audit SEO"},
    )
    assert response.status_code == 201
    assert response.json()["branch"] == "master"


async def test_get_workflow_via_api(client: AsyncClient):
    create_response = await client.post(
        "/api/workflows",
        json={"repository_url": "https://github.com/example/project", "goal": "Audit SEO"},
    )
    workflow_id = create_response.json()["id"]

    get_response = await client.get(f"/api/workflows/{workflow_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == workflow_id


async def test_get_workflow_not_found_returns_error_envelope(client: AsyncClient):
    response = await client.get(f"/api/workflows/{uuid.uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "WORKFLOW_NOT_FOUND"


async def test_create_workflow_rejects_invalid_url(client: AsyncClient):
    response = await client.post(
        "/api/workflows",
        json={"repository_url": "not-a-url", "goal": "Audit SEO"},
    )
    assert response.status_code == 422


@pytest.mark.usefixtures("setup_db")
async def test_workflow_service_create_and_get(db_session: AsyncSession):
    repository = PostgresWorkflowRepository(db_session)
    service = WorkflowService(repository)

    created = await service.create_workflow(
        repository_url="https://github.com/example/project", goal="Audit SEO"
    )
    assert created.status == WorkflowStatus.PENDING

    fetched = await service.get_workflow(created.id)
    assert fetched is not None
    assert fetched.id == created.id


async def test_workflow_service_get_missing_returns_none(db_session: AsyncSession):
    repository = PostgresWorkflowRepository(db_session)
    service = WorkflowService(repository)

    assert await service.get_workflow(uuid.uuid4()) is None
