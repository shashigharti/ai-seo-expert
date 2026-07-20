from typing import Any

from app.agents.managers.fix_manager import FixManagerAgent
from app.agents.workers.fix_worker import FixWorkerAgent
from app.domain.models.patch import FixGroup
from app.domain.models.stored_finding import StoredFinding
from app.domain.models.task import Task
from app.domain.models.workflow import Workflow
from app.ports.git_provider import GitProvider
from app.ports.repositories import TaskRepository
from app.tools.github_file_reader import read_repository_file


class PullRequestGroupExecutor:
    """`TaskExecutor` (app/application/orchestrator/executor.py) for one
    FixGroup - one PR generation attempt. Dispatched through the same
    `Orchestrator` the SEO capability workers use (app/application/
    orchestrator/orchestrator.py), so a transient GitHub/Qwen failure gets
    the same retry/backoff treatment instead of failing the group outright.

    Raises on failure rather than catching - Orchestrator.dispatch already
    classifies and retries/records exceptions; catching here would just
    hide failures from that machinery.
    """

    def __init__(
        self,
        workflow: Workflow,
        group: FixGroup,
        group_findings: list[StoredFinding],
        fix_manager: FixManagerAgent,
        fix_worker: FixWorkerAgent,
        task_repository: TaskRepository,
        git_provider: GitProvider,
    ) -> None:
        self.workflow = workflow
        self.group = group
        self.group_findings = group_findings
        self.fix_manager = fix_manager
        self.fix_worker = fix_worker
        self.task_repository = task_repository
        self.git_provider = git_provider

    async def execute(self, task: Task) -> dict[str, Any]:
        branch_name = self.fix_manager.branch_name_for(self.group)

        patches = []
        input_tokens = 0
        output_tokens = 0
        reasoning_tokens = 0
        for stored in self.group_findings:
            finding_task = await self.task_repository.get(stored.task_id)
            scope = finding_task.input.get("scope", {}) if finding_task else {}
            files = scope.get("files", []) if isinstance(scope, dict) else []
            file_path = files[0] if files else f"{stored.finding.category}-fix-notes.md"

            current_content = None
            if finding_task and files:
                ref = finding_task.input.get("ref", "master")
                current_content = await read_repository_file(self.workflow.repository_url, file_path, ref=ref)

            patch = await self.fix_worker.propose_patch(stored.finding, file_path, current_content)
            patches.append(patch)
            if self.fix_worker.last_usage is not None:
                input_tokens += self.fix_worker.last_usage.input_tokens
                output_tokens += self.fix_worker.last_usage.output_tokens
                reasoning_tokens += self.fix_worker.last_usage.reasoning_tokens or 0

        pr_description = await self.fix_manager.draft_pr_description(
            self.group, [f.finding for f in self.group_findings]
        )
        if self.fix_manager.last_usage is not None:
            input_tokens += self.fix_manager.last_usage.input_tokens
            output_tokens += self.fix_manager.last_usage.output_tokens
            reasoning_tokens += self.fix_manager.last_usage.reasoning_tokens or 0

        base_branch = await self.git_provider.get_default_branch(self.workflow.repository_url)
        url = await self.git_provider.open_pull_request(
            repository_url=self.workflow.repository_url,
            base_branch=base_branch,
            new_branch=branch_name,
            patches=patches,
            pr_title=pr_description.title,
            pr_body=pr_description.body,
        )

        return {
            "status": "opened",
            "url": url,
            "branch_name": branch_name,
            "commit_summary": pr_description.title,
            "agent_name": "FixManagerAgent",
            "model": self.fix_worker.model,
            "token_usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "reasoning_tokens": reasoning_tokens or None,
            },
        }
