from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.models.finding import FindingModel
from app.domain.models.stored_finding import StoredFinding


class PostgresResultRepository:
    """Adapter implementing the ResultRepository port via SQLAlchemy."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save_many(self, findings: list[StoredFinding]) -> list[StoredFinding]:
        rows = [
            FindingModel(
                id=f.id,
                workflow_id=f.workflow_id,
                task_id=f.task_id,
                agent_name=f.agent_name,
                finding=f.finding.model_dump(mode="json"),
                status=f.status.value,
            )
            for f in findings
        ]
        self.db.add_all(rows)
        await self.db.commit()
        for row in rows:
            await self.db.refresh(row)
        return [StoredFinding.model_validate(row) for row in rows]

    async def list_for_workflow(self, workflow_id: UUID) -> list[StoredFinding]:
        result = await self.db.execute(
            select(FindingModel).where(FindingModel.workflow_id == workflow_id).order_by(FindingModel.created_at)
        )
        return [StoredFinding.model_validate(row) for row in result.scalars()]

    async def get_many(self, finding_ids: list[UUID]) -> list[StoredFinding]:
        result = await self.db.execute(select(FindingModel).where(FindingModel.id.in_(finding_ids)))
        return [StoredFinding.model_validate(row) for row in result.scalars()]

    async def mark_status(self, finding_ids: list[UUID], status: str) -> None:
        result = await self.db.execute(select(FindingModel).where(FindingModel.id.in_(finding_ids)))
        for row in result.scalars():
            row.status = status
        await self.db.commit()
