import re
import uuid
from typing import Any

from app.agents.factory import AgentFactory
from app.application.orchestrator.orchestrator import Orchestrator
from app.application.pull_requests.group_executor import PullRequestGroupExecutor
from app.config.logging import get_logger
from app.domain.enums.finding_status import FindingStatus
from app.domain.models.task import Task
from app.ports.event_publisher import EventPublisher
from app.ports.repositories import ResultRepository, TaskRepository, WorkflowRepository

logger = get_logger(__name__)

# Every PR-generation task's capability carries this prefix - the only
# thing that distinguishes it, on the wire, from a SEO analysis capability
# task (both are plain Task rows dispatched through the same Orchestrator;
# see orchestrator.py's docstring). The frontend's SEO Agent Execution and
# GitHub PR Agent Execution panels filter on this same prefix.
CAPABILITY_PREFIX = "pull_request_"


def _slugify(text: str, max_length: int = 30) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_length] or "fix"


class WorkflowNotFoundForPullRequestError(Exception):
    pass


class NoApprovedFindingsError(Exception):
    pass


def pr_completion_event_data(task: Task) -> dict[str, Any] | None:
    """Enriches a PR-generation task.completed event for the GitHub PR
    Agent Execution panel. Unlike the SEO Agent Execution Panel's
    `_completion_event_data` (orchestrator.py), a PR group's task.output is
    never AgentResult-shaped - it's exactly the dict `PullRequestGroupExecutor.
    execute()` returned, so this reads it directly rather than parsing.
    """
    if task.output is None:
        return None
    return {
        "agent_name": task.output.get("agent_name"),
        "model": task.output.get("model"),
        "token_usage": task.output.get("token_usage"),
        "duration_seconds": (
            (task.updated_at - task.started_at).total_seconds() if task.started_at else None
        ),
        "branch_name": task.output.get("branch_name"),
        "commit_summary": task.output.get("commit_summary"),
        "url": task.output.get("url"),
    }


class PullRequestService:
    """docs/architecture.md §7 Main Workflow: "Fix Manager creates
    implementation tasks" -> "GitHub PR Generator opens pull request".

    Split into a fast, request-scoped `start_generation` (validates and
    creates one PENDING Task per FixGroup) and the slow, background-scoped
    dispatch (`app/application/workflows/pull_request_runner.py`'s
    `run_pull_request_generation`) - same split `run_seo_analysis`/
    `_dispatch_capability` already use for SEO analysis, so PR generation
    gets real, live, per-group progress instead of the caller blocking on
    the whole batch.
    """

    def __init__(
        self,
        workflow_repository: WorkflowRepository,
        task_repository: TaskRepository,
        result_repository: ResultRepository,
        agent_factory: AgentFactory,
        event_publisher: EventPublisher,
    ) -> None:
        self.workflow_repository = workflow_repository
        self.task_repository = task_repository
        self.result_repository = result_repository
        self.agent_factory = agent_factory
        self.event_publisher = event_publisher

    async def start_generation(self, workflow_id: uuid.UUID, pr_strategy: str) -> list[Task]:
        """Validates the request and creates one PENDING task per FixGroup -
        the actual patch/PR-opening work happens later, in the background
        (see `run_pull_request_generation`). Returns the created tasks so
        the route can hand them to `background_tasks.add_task`.
        """
        workflow = await self.workflow_repository.get(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundForPullRequestError(str(workflow_id))

        all_findings = await self.result_repository.list_for_workflow(workflow_id)
        approved = [f for f in all_findings if f.status == FindingStatus.APPROVED]
        if not approved:
            raise NoApprovedFindingsError(str(workflow_id))

        fix_manager = self.agent_factory.create("fix_manager")
        groups = fix_manager.group_approved_findings(approved, pr_strategy)

        orchestrator = Orchestrator(self.task_repository, self.event_publisher)
        tasks: list[Task] = []
        for group in groups:
            group_finding_ids = [str(f.id) for f in approved if f.id in group.finding_ids]
            task = await orchestrator.create_task(
                workflow_id=workflow_id,
                capability=f"{CAPABILITY_PREFIX}{_slugify(group.label)}",
                input={
                    "group_label": group.label,
                    "finding_ids": group_finding_ids,
                    "pr_strategy": pr_strategy,
                },
            )
            tasks.append(task)
        return tasks
