from collections import Counter
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from pydantic import BaseModel

from app.api.dependencies import (
    ApprovalServiceDep,
    EventPublisherDep,
    PullRequestRepositoryDep,
    PullRequestServiceDep,
    TaskRepositoryDep,
    WorkflowServiceDep,
)
from app.api.schemas.finding import ApprovalRequest, ApprovalResponse, FindingListResponse, FindingResponse
from app.api.schemas.pull_request import (
    PullRequestGenerationStartedResponse,
    PullRequestListResponse,
    PullRequestResponse,
)
from app.api.schemas.task import TaskListResponse, task_to_response
from app.api.schemas.workflow import WorkflowCreateRequest, WorkflowResponse
from app.application.approvals.service import UnknownFindingIdsError
from app.application.pull_requests.service import NoApprovedFindingsError, WorkflowNotFoundForPullRequestError
from app.application.validation.schema_validator import validate_agent_result
from app.application.workflows.analysis_runner import run_seo_analysis
from app.application.workflows.pull_request_runner import run_pull_request_generation

# No auth on any route in this file. Phase 10 (review/CHANGELOG.md) had
# gated the three mutating routes (create/approve/generate-PRs) behind
# ActiveUserDep, deliberately leaving GET routes public since there was no
# frontend login UI to use a login wall anyway. That gap was later found
# but left unresolved pending a scoping decision (same changelog, "Design
# polish pass" entry): apiClient.ts never attached an Authorization header
# and no login/register UI was ever built, so every mutating call from the
# real frontend 401'd unconditionally. Given there's still no login UI,
# auth was dropped from these routes too - real per-user accounts/JWT still
# exist and work (app/api/routes/auth.py), just no longer required here.
router = APIRouter()


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreateRequest,
    service: WorkflowServiceDep,
    background_tasks: BackgroundTasks,
) -> WorkflowResponse:
    workflow = await service.create_workflow(
        repository_url=str(payload.repository_url),
        goal=payload.goal,
        branch=payload.branch,
    )
    # docs/architecture.md §7: workflow creation kicks off manager planning
    # and worker dispatch; progress streams via GET /events (SSE).
    background_tasks.add_task(run_seo_analysis, workflow.id)
    return WorkflowResponse.model_validate(workflow)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID, service: WorkflowServiceDep) -> WorkflowResponse:
    workflow = await service.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "The requested workflow was not found"},
        )
    return WorkflowResponse.model_validate(workflow)


@router.get("/{workflow_id}/tasks", response_model=TaskListResponse)
async def list_tasks(workflow_id: UUID, task_repository: TaskRepositoryDep) -> TaskListResponse:
    """Backs the Agent Execution Panel's initial snapshot (docs/specs.md
    §4) - SSE (GET /{workflow_id}/events) only pushes deltas from the
    moment of connection, so a client loading the page mid-workflow needs
    this to reconstruct current state. No auth, matching every other route
    in this file - see the module docstring above `router = APIRouter()`.
    """
    tasks = await task_repository.list_for_workflow(workflow_id)
    return TaskListResponse(
        items=[task_to_response(task, validate_agent_result(task.output or {})) for task in tasks]
    )


@router.get("/{workflow_id}/events")
async def stream_workflow_events(
    workflow_id: UUID, request: Request, event_publisher: EventPublisherDep
) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        async for event in event_publisher.subscribe(workflow_id):
            if await request.is_disconnected():
                break
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{workflow_id}/findings", response_model=FindingListResponse)
async def get_findings(workflow_id: UUID, service: ApprovalServiceDep) -> FindingListResponse:
    findings = await service.list_findings(workflow_id)
    return FindingListResponse(
        total=len(findings),
        findings_by_category=dict(Counter(f.finding.category for f in findings)),
        findings_by_severity=dict(Counter(f.finding.severity for f in findings)),
        items=[FindingResponse.model_validate(f) for f in findings],
    )


@router.post("/{workflow_id}/approvals", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
async def approve_findings(
    workflow_id: UUID, payload: ApprovalRequest, service: ApprovalServiceDep
) -> ApprovalResponse:
    try:
        approval = await service.approve(workflow_id, payload.finding_ids, payload.pr_strategy)
    except UnknownFindingIdsError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "FINDING_NOT_FOUND",
                "message": f"Unknown finding id(s): {[str(i) for i in exc.missing_ids]}",
            },
        ) from exc
    return ApprovalResponse.model_validate(approval)


class GeneratePullRequestsRequest(BaseModel):
    pr_strategy: str = "by_category"


@router.post(
    "/{workflow_id}/pull-requests",
    response_model=PullRequestGenerationStartedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_pull_requests(
    workflow_id: UUID,
    payload: GeneratePullRequestsRequest,
    service: PullRequestServiceDep,
    background_tasks: BackgroundTasks,
) -> PullRequestGenerationStartedResponse:
    """Kicks off PR generation and returns immediately - one Task per
    FixGroup is created (still PENDING) before this responds, then dispatched
    in the background by `run_pull_request_generation`. Progress streams via
    the same GET /events SSE stream analysis tasks use (docs/api-contracts.md),
    filtered by clients on the `pull_request_` capability prefix; final
    results are read via GET /pull-requests below.
    """
    try:
        tasks = await service.start_generation(workflow_id, payload.pr_strategy)
    except WorkflowNotFoundForPullRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "WORKFLOW_NOT_FOUND", "message": "The requested workflow was not found"},
        ) from exc
    except NoApprovedFindingsError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_APPROVED_FINDINGS",
                "message": "No approved findings to generate a pull request for",
            },
        ) from exc
    background_tasks.add_task(run_pull_request_generation, workflow_id, tasks)
    return PullRequestGenerationStartedResponse(task_ids=[t.id for t in tasks])


@router.get("/{workflow_id}/pull-requests", response_model=PullRequestListResponse)
async def list_pull_requests(
    workflow_id: UUID, pull_request_repository: PullRequestRepositoryDep
) -> PullRequestListResponse:
    """Final, terminal PR generation results - didn't exist before this was
    async (the old synchronous POST returned these directly); now the
    frontend reads them here once GET /events shows a group's task settled.
    """
    results = await pull_request_repository.list_for_workflow(workflow_id)
    return PullRequestListResponse(items=[PullRequestResponse.model_validate(r) for r in results])
