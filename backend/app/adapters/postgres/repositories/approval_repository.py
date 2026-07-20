from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.models.approval import ApprovalModel
from app.domain.models.approval import Approval


class PostgresApprovalRepository:
    """Adapter implementing the ApprovalRepository port via SQLAlchemy."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, approval: Approval) -> Approval:
        row = ApprovalModel(
            id=approval.id,
            workflow_id=approval.workflow_id,
            finding_ids=[str(fid) for fid in approval.finding_ids],
            pr_strategy=approval.pr_strategy,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return Approval.model_validate(row)

    async def list_for_workflow(self, workflow_id: UUID) -> list[Approval]:
        result = await self.db.execute(
            select(ApprovalModel)
            .where(ApprovalModel.workflow_id == workflow_id)
            .order_by(ApprovalModel.created_at)
        )
        return [Approval.model_validate(row) for row in result.scalars()]
