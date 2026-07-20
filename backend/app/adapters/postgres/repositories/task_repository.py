from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.models.task import TaskModel
from app.domain.models.task import Task


class PostgresTaskRepository:
    """Adapter implementing the TaskRepository port via SQLAlchemy."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, task: Task) -> Task:
        row = TaskModel(
            id=task.id,
            workflow_id=task.workflow_id,
            capability=task.capability,
            status=task.status.value,
            input=task.input,
            output=task.output,
            started_at=task.started_at,
            attempt=task.attempt,
            max_attempts=task.max_attempts,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return Task.model_validate(row)

    async def get(self, task_id: UUID) -> Task | None:
        row = await self.db.get(TaskModel, task_id)
        if row is None:
            return None
        return Task.model_validate(row)

    async def update(self, task: Task) -> Task:
        row = await self.db.get(TaskModel, task.id)
        if row is None:
            raise ValueError(f"Task {task.id} does not exist")
        row.status = task.status.value
        row.output = task.output
        row.error_message = task.error_message
        row.started_at = task.started_at
        row.attempt = task.attempt
        row.max_attempts = task.max_attempts
        await self.db.commit()
        await self.db.refresh(row)
        return Task.model_validate(row)

    async def list_for_workflow(self, workflow_id: UUID) -> list[Task]:
        result = await self.db.execute(
            select(TaskModel).where(TaskModel.workflow_id == workflow_id).order_by(TaskModel.created_at)
        )
        return [Task.model_validate(row) for row in result.scalars()]
