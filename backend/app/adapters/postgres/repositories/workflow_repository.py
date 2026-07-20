from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.models.workflow import WorkflowModel
from app.domain.models.workflow import Workflow


class PostgresWorkflowRepository:
    """Adapter implementing the WorkflowRepository port via SQLAlchemy."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, workflow: Workflow) -> Workflow:
        row = WorkflowModel(
            id=workflow.id,
            repository_url=workflow.repository_url,
            branch=workflow.branch,
            goal=workflow.goal,
            status=workflow.status.value,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return Workflow.model_validate(row)

    async def get(self, workflow_id: UUID) -> Workflow | None:
        row = await self.db.get(WorkflowModel, workflow_id)
        if row is None:
            return None
        return Workflow.model_validate(row)

    async def update(self, workflow: Workflow) -> Workflow:
        row = await self.db.get(WorkflowModel, workflow.id)
        if row is None:
            raise ValueError(f"Workflow {workflow.id} does not exist")
        row.status = workflow.status.value
        row.error_message = workflow.error_message
        await self.db.commit()
        await self.db.refresh(row)
        return Workflow.model_validate(row)
