import uuid
from datetime import datetime, timezone

from app.application.memory.service import MemoryService
from app.domain.enums.finding_status import FindingStatus
from app.domain.models.approval import Approval
from app.domain.models.stored_finding import StoredFinding
from app.ports.repositories import ApprovalRepository, ResultRepository, WorkflowRepository


class UnknownFindingIdsError(Exception):
    def __init__(self, missing_ids: list[uuid.UUID]) -> None:
        super().__init__(f"Unknown finding id(s): {missing_ids}")
        self.missing_ids = missing_ids


class WorkflowNotFoundForApprovalError(Exception):
    pass


class ApprovalService:
    def __init__(
        self,
        result_repository: ResultRepository,
        approval_repository: ApprovalRepository,
        workflow_repository: WorkflowRepository,
        memory_service: MemoryService,
    ) -> None:
        self.result_repository = result_repository
        self.approval_repository = approval_repository
        self.workflow_repository = workflow_repository
        self.memory_service = memory_service

    async def list_findings(self, workflow_id: uuid.UUID) -> list[StoredFinding]:
        return await self.result_repository.list_for_workflow(workflow_id)

    async def approve(
        self, workflow_id: uuid.UUID, finding_ids: list[uuid.UUID], pr_strategy: str
    ) -> Approval:
        workflow = await self.workflow_repository.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundForApprovalError(str(workflow_id))

        found = await self.result_repository.get_many(finding_ids)
        found_ids = {f.id for f in found}
        missing = [fid for fid in finding_ids if fid not in found_ids]
        if missing:
            raise UnknownFindingIdsError(missing)

        await self.result_repository.mark_status(finding_ids, FindingStatus.APPROVED.value)
        # docs/agent-architecture.md §12: approved decisions are part of what
        # memory should store, so future workflows on this repository know
        # what's already been fixed.
        await self.memory_service.record_approved_decision(
            workflow.repository_url, [f.finding for f in found], pr_strategy
        )

        approval = Approval(
            id=uuid.uuid4(),
            workflow_id=workflow_id,
            finding_ids=finding_ids,
            pr_strategy=pr_strategy,
            created_at=datetime.now(timezone.utc),
        )
        return await self.approval_repository.create(approval)
