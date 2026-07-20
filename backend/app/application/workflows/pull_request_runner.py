import asyncio
import uuid
from datetime import datetime, timezone

from app.adapters.events.sse_publisher import sse_event_publisher
from app.adapters.github.provider import GitHubProvider
from app.adapters.postgres.database import SessionLocal
from app.adapters.postgres.repositories.pull_request_repository import PostgresPullRequestRepository
from app.adapters.postgres.repositories.result_repository import PostgresResultRepository
from app.adapters.postgres.repositories.task_repository import PostgresTaskRepository
from app.adapters.postgres.repositories.workflow_repository import PostgresWorkflowRepository
from app.adapters.qwen.model_client import QwenCloudModelClient
from app.agents.bootstrap import build_agent_factory
from app.application.orchestrator.orchestrator import Orchestrator
from app.application.pull_requests.group_executor import PullRequestGroupExecutor
from app.application.pull_requests.service import pr_completion_event_data
from app.config.logging import get_logger
from app.config.settings import settings
from app.domain.enums.task_status import TaskStatus
from app.domain.models.patch import FixGroup
from app.domain.models.pull_request import PullRequestResult
from app.domain.models.task import Task

logger = get_logger(__name__)

# Groups dispatch concurrently, capped for the same reason
# analysis_runner._dispatch_capability caps SEO capability dispatch - avoid
# firing an unbounded burst of Qwen/GitHub calls at once.
_MAX_CONCURRENT_PR_DISPATCHES = 3

# A PR group's single attempt is several sequential real network calls, not
# one: propose_patch per finding + draft_pr_description (Qwen) followed by
# get_default_branch + create_git_ref + a get/update/create_file per patch +
# create_pull (GitHub) - all inside one Orchestrator.dispatch attempt.
# Orchestrator's own default (30s, sized for a single SEO capability's one
# LLM call) isn't enough headroom for that chain; a real run against
# octocat/Spoon-Knife confirmed attempts genuinely timing out (asyncio.
# TimeoutError, which logs as an empty message) well before finishing.
_PR_GENERATION_TIMEOUT_SECONDS = 120.0


async def _dispatch_pull_request_task(
    workflow_id: uuid.UUID,
    task_id: uuid.UUID,
    factory,
    git_provider,
    semaphore: asyncio.Semaphore,
) -> Task | None:
    """Dispatches one FixGroup's PR-generation task on its own DB session -
    same per-coroutine-session reasoning as analysis_runner._dispatch_capability
    (SQLAlchemy's AsyncSession isn't safe for concurrent use). Persists the
    resulting PullRequestResult once the task reaches a terminal state,
    replacing the try/except-and-create the old synchronous
    generate_pull_requests used to do inline.
    """
    async with semaphore, SessionLocal() as session:
        task_repository = PostgresTaskRepository(session)
        task = await task_repository.get(task_id)
        if task is None:
            logger.warning("run_pull_request_generation: task %s not found", task_id)
            return None

        workflow_repository = PostgresWorkflowRepository(session)
        workflow = await workflow_repository.get(workflow_id)
        if workflow is None:
            logger.warning("run_pull_request_generation: workflow %s not found", workflow_id)
            return None

        result_repository = PostgresResultRepository(session)
        finding_ids = [uuid.UUID(fid) for fid in task.input.get("finding_ids", [])]
        group_findings = await result_repository.get_many(finding_ids)
        group = FixGroup(label=task.input.get("group_label", task.capability), finding_ids=finding_ids)

        executor = PullRequestGroupExecutor(
            workflow=workflow,
            group=group,
            group_findings=group_findings,
            fix_manager=factory.create("fix_manager"),
            fix_worker=factory.create("fix_worker"),
            task_repository=task_repository,
            git_provider=git_provider,
        )
        orchestrator = Orchestrator(
            task_repository,
            sse_event_publisher,
            timeout_seconds=_PR_GENERATION_TIMEOUT_SECONDS,
            completion_event_data=pr_completion_event_data,
        )
        completed = await orchestrator.dispatch(task, executor)

        pull_request_repository = PostgresPullRequestRepository(session)
        output = completed.output or {}
        if completed.status == TaskStatus.COMPLETED:
            result = PullRequestResult(
                id=uuid.uuid4(),
                workflow_id=workflow_id,
                status="opened",
                url=output.get("url"),
                repository_url=workflow.repository_url,
                branch_name=output.get("branch_name") or "",
                commit_summary=output.get("commit_summary") or group.label,
                finding_ids=finding_ids,
                error_message=None,
                created_at=datetime.now(timezone.utc),
            )
        else:
            result = PullRequestResult(
                id=uuid.uuid4(),
                workflow_id=workflow_id,
                status="failed",
                url=None,
                repository_url=workflow.repository_url,
                branch_name="",
                commit_summary=group.label,
                finding_ids=finding_ids,
                error_message=completed.error_message,
                created_at=datetime.now(timezone.utc),
            )
        await pull_request_repository.create(result)
        return completed


async def run_pull_request_generation(workflow_id: uuid.UUID, tasks: list[Task]) -> None:
    """Background-task entry point kicked off by
    POST /api/workflows/{id}/pull-requests (app/api/routes/workflows.py),
    mirroring analysis_runner.run_seo_analysis's pattern: runs detached from
    the request that scheduled it, so it opens its own DB session/engine and
    its own AgentFactory/GitProvider rather than reusing the request's.
    """
    model_client = QwenCloudModelClient(api_key=settings.qwen_api_key, base_url=settings.qwen_base_url)
    factory = build_agent_factory(model_client)
    git_provider = GitHubProvider(token=settings.github_token)

    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_PR_DISPATCHES)
    results = await asyncio.gather(
        *(_dispatch_pull_request_task(workflow_id, task.id, factory, git_provider, semaphore) for task in tasks),
        return_exceptions=True,
    )
    for task, result in zip(tasks, results):
        if isinstance(result, Exception):
            logger.error(
                "Workflow %s: PR generation dispatch failed for task %s: %s", workflow_id, task.id, result
            )
