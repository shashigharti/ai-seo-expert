import uuid

from app.agents.base import BaseAgent
from app.config.logging import get_logger
from app.domain.models.agent_result import AgentResult
from app.domain.models.manager_decision import (
    ManagerDecision,
    PlannedCapability,
    SEOEvaluationOutput,
    SEOPlanOutput,
)
from app.domain.models.task import Task
from app.domain.models.task_brief import TaskBrief
from app.domain.models.workflow import Workflow
from app.tools.github_file_reader import list_repository_files

logger = get_logger(__name__)

_EXPECTED_OUTPUT_BY_CAPABILITY = {
    "technical_seo": "TechnicalSEOResult",
    "metadata": "MetadataResult",
    "content_seo": "ContentSEOResult",
    "accessibility": "AccessibilityResult",
    "performance": "PerformanceResult",
}


def _expected_output_for(capability: str) -> str:
    return _EXPECTED_OUTPUT_BY_CAPABILITY.get(capability, f"{capability}Result")


async def _repository_files_section(repository_url: str, ref: str) -> str:
    """Real file listing for the planning prompt - without this, scope.files
    was pure LLM guesswork with zero visibility into what's actually in the
    repository, so a guessed filename that doesn't exist silently produced
    "0 findings, no such files" regardless of where in the repo the real
    files actually live. Falls back to no listing (today's prior baseline)
    on any failure - a listing hiccup must not fail the whole workflow.
    """
    try:
        files = await list_repository_files(repository_url, ref=ref)
    except Exception:
        logger.warning(
            "Could not list repository files for %s@%s; planning without a real listing",
            repository_url,
            ref,
        )
        return ""

    if not files:
        return "\n\nRepository file listing: no files found (empty repository, or listing unavailable)."
    return (
        "\n\nRepository files (real listing - base scope.files on these paths; "
        "do not invent filenames that aren't listed here):\n" + "\n".join(files)
    )


def _brief_from_planned(workflow_id: uuid.UUID, planned: PlannedCapability) -> TaskBrief:
    return TaskBrief(
        id=uuid.uuid4(),
        workflow_id=workflow_id,
        capability=planned.capability,
        objective=planned.objective,
        scope=planned.scope,
        constraints=planned.constraints,
        acceptance_criteria=planned.acceptance_criteria,
        expected_output=_expected_output_for(planned.capability),
        priority=planned.priority,
    )


class SEOManagerAgent(BaseAgent):
    """docs/agent-architecture.md - SEO Review Manager: decomposes a
    workflow goal into worker tasks, and later decides whether analysis is
    complete or needs follow-up (§7 Task Creation, §11 Analysis follow-up).

    Deliberately does not implement the generic `Agent.execute(task)` shape
    - a manager plans/evaluates against a *workflow*, not a single task; see
    `plan()` and `evaluate()` below instead.
    """

    def __init__(self, name, capability, model_client, tools, skill, model, thinking=False):
        super().__init__(
            name=name,
            capability=capability,
            model_client=model_client,
            tools=tools,
            skill=skill,
            output_model=SEOPlanOutput,
            model=model,
            thinking=thinking,
        )

    async def plan(self, workflow: Workflow, memory_context: str = "") -> list[TaskBrief]:
        memory_section = f"\n\n{memory_context}\n" if memory_context else ""
        files_section = await _repository_files_section(workflow.repository_url, workflow.branch)
        user_prompt = (
            f"Workflow goal: {workflow.goal}\n"
            f"Repository: {workflow.repository_url}\n"
            f"Branch: {workflow.branch}"
            f"{memory_section}"
            f"{files_section}\n\n"
            "Decide which worker capabilities are needed and produce one task per capability. "
            "If prior context lists known false positives, do not re-create tasks solely to "
            "re-investigate them unless the current goal specifically calls for it."
        )
        response = await self.model_client.run(
            system_prompt=self.skill,
            user_prompt=user_prompt,
            output_type=SEOPlanOutput,
            model=self.model,
            thinking=self.thinking,
        )
        return [_brief_from_planned(workflow.id, planned) for planned in response.output.capabilities]

    async def evaluate(self, workflow: Workflow, results: list[AgentResult]) -> ManagerDecision:
        findings_summary = "\n".join(
            f"- [{r.agent_name}] status={r.status}, confidence={r.confidence}, "
            f"findings={len(r.findings)}, suggestions="
            f"{[s.model_dump() for s in r.follow_up_suggestions]}"
            for r in results
        )
        user_prompt = (
            f"Workflow goal: {workflow.goal}\n\n"
            f"Worker results so far:\n{findings_summary}\n\n"
            "Decide whether analysis is complete, or which follow-up tasks (if any) to create."
        )
        response = await self.model_client.run(
            system_prompt=self.skill,
            user_prompt=user_prompt,
            output_type=SEOEvaluationOutput,
            model=self.model,
            thinking=self.thinking,
        )
        return ManagerDecision(
            is_complete=response.output.is_complete,
            rationale=response.output.rationale,
            follow_up_briefs=[
                _brief_from_planned(workflow.id, planned)
                for planned in response.output.follow_up_capabilities
            ],
        )

    async def execute(self, task: Task) -> AgentResult:
        raise NotImplementedError(
            "SEOManagerAgent plans/evaluates workflows via plan()/evaluate(); "
            "it does not execute individual tasks like a worker agent."
        )
