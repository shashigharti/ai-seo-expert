from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.models.pull_request import PullRequestModel
from app.domain.models.pull_request import PullRequestResult


class PostgresPullRequestRepository:
    """Adapter implementing the PullRequestRepository port via SQLAlchemy."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, pull_request: PullRequestResult) -> PullRequestResult:
        row = PullRequestModel(
            id=pull_request.id,
            workflow_id=pull_request.workflow_id,
            status=pull_request.status,
            url=pull_request.url,
            repository_url=pull_request.repository_url,
            branch_name=pull_request.branch_name,
            commit_summary=pull_request.commit_summary,
            finding_ids=[str(fid) for fid in pull_request.finding_ids],
            error_message=pull_request.error_message,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return PullRequestResult.model_validate(row)

    async def list_for_workflow(self, workflow_id: UUID) -> list[PullRequestResult]:
        result = await self.db.execute(
            select(PullRequestModel)
            .where(PullRequestModel.workflow_id == workflow_id)
            .order_by(PullRequestModel.created_at)
        )
        return [PullRequestResult.model_validate(row) for row in result.scalars()]
