import uuid
from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.repositories.result_repository import PostgresResultRepository
from app.adapters.postgres.repositories.task_repository import PostgresTaskRepository
from app.domain.enums.task_status import TaskStatus
from app.domain.models.agent_result import Finding
from app.domain.models.stored_finding import StoredFinding
from app.domain.models.task import Task


async def _seed_workflow_with_findings(client: AsyncClient, db_session: AsyncSession) -> str:
    create_response = await client.post(
        "/api/workflows",
        json={"repository_url": "https://github.com/example/project", "goal": "Audit SEO"},
    )
    workflow_id = create_response.json()["id"]

    now = datetime.now(timezone.utc)
    task = await PostgresTaskRepository(db_session).create(
        Task(
            id=uuid.uuid4(),
            workflow_id=uuid.UUID(workflow_id),
            capability="technical_seo",
            status=TaskStatus.COMPLETED,
            created_at=now,
            updated_at=now,
        )
    )
    findings = [
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
            created_at=now,
        ),
        StoredFinding(
            id=uuid.uuid4(),
            workflow_id=uuid.UUID(workflow_id),
            task_id=task.id,
            agent_name="TechnicalSEOAgent",
            finding=Finding(
                category="metadata",
                severity="medium",
                title="Missing meta description",
                description="desc",
                evidence="index.html line 5",
                recommendation="add one",
            ),
            created_at=now,
        ),
    ]
    await PostgresResultRepository(db_session).save_many(findings)
    return workflow_id


async def test_get_findings_returns_grouped_counts(client: AsyncClient, db_session: AsyncSession):
    workflow_id = await _seed_workflow_with_findings(client, db_session)

    response = await client.get(f"/api/workflows/{workflow_id}/findings")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["findings_by_category"] == {"crawlability": 1, "metadata": 1}
    assert body["findings_by_severity"] == {"high": 1, "medium": 1}
    assert len(body["items"]) == 2
    assert body["items"][0]["status"] == "pending"


async def test_get_findings_empty_workflow_returns_zero_totals(client: AsyncClient):
    create_response = await client.post(
        "/api/workflows",
        json={"repository_url": "https://github.com/example/project", "goal": "Audit SEO"},
    )
    workflow_id = create_response.json()["id"]

    response = await client.get(f"/api/workflows/{workflow_id}/findings")

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "findings_by_category": {},
        "findings_by_severity": {},
        "items": [],
    }


async def test_approve_findings_success(client: AsyncClient, db_session: AsyncSession):
    workflow_id = await _seed_workflow_with_findings(client, db_session)
    findings_response = await client.get(f"/api/workflows/{workflow_id}/findings")
    finding_ids = [item["id"] for item in findings_response.json()["items"]]

    response = await client.post(
        f"/api/workflows/{workflow_id}/approvals",
        json={"finding_ids": [finding_ids[0]], "pr_strategy": "by_category"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["workflow_id"] == workflow_id
    assert body["finding_ids"] == [finding_ids[0]]
    assert body["pr_strategy"] == "by_category"

    findings_response = await client.get(f"/api/workflows/{workflow_id}/findings")
    statuses = {item["id"]: item["status"] for item in findings_response.json()["items"]}
    assert statuses[finding_ids[0]] == "approved"
    assert statuses[finding_ids[1]] == "pending"


async def test_approve_findings_rejects_unknown_id(client: AsyncClient, db_session: AsyncSession):
    workflow_id = await _seed_workflow_with_findings(client, db_session)

    response = await client.post(
        f"/api/workflows/{workflow_id}/approvals",
        json={"finding_ids": [str(uuid.uuid4())], "pr_strategy": "by_category"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FINDING_NOT_FOUND"


async def test_approve_findings_rejects_empty_finding_ids(client: AsyncClient):
    create_response = await client.post(
        "/api/workflows",
        json={"repository_url": "https://github.com/example/project", "goal": "Audit SEO"},
    )
    workflow_id = create_response.json()["id"]

    response = await client.post(
        f"/api/workflows/{workflow_id}/approvals",
        json={"finding_ids": [], "pr_strategy": "by_category"},
    )

    assert response.status_code == 422
