import uuid
from datetime import datetime, timezone

from app.domain.enums.workflow_status import WorkflowStatus
from app.domain.models.workflow import DEFAULT_GOAL, Workflow
from app.ports.repositories import WorkflowRepository


class WorkflowService:
    def __init__(self, repository: WorkflowRepository) -> None:
        self.repository = repository

    async def create_workflow(
        self, repository_url: str, branch: str = "master", goal: str = DEFAULT_GOAL
    ) -> Workflow:
        now = datetime.now(timezone.utc)
        workflow = Workflow(
            id=uuid.uuid4(),
            repository_url=repository_url,
            branch=branch,
            goal=goal,
            status=WorkflowStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        return await self.repository.create(workflow)

    async def get_workflow(self, workflow_id: uuid.UUID) -> Workflow | None:
        return await self.repository.get(workflow_id)
