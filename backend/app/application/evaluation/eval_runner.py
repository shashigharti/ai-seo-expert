import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.agents.factory import AgentFactory
from app.config.logging import get_logger
from app.domain.enums.task_status import TaskStatus
from app.domain.enums.workflow_status import WorkflowStatus
from app.domain.models.agent_result import AgentResult, Finding
from app.domain.models.eval_case import EvalCase
from app.domain.models.eval_result import EvalCaseResult, EvalRunSummary
from app.domain.models.manager_decision import PlannedCapability
from app.domain.models.task import Task
from app.domain.models.workflow import Workflow
from app.domain.policies.eval_scoring import overall_score, score_output, score_trajectory

logger = get_logger(__name__)


def load_eval_cases(path: Path) -> list[EvalCase]:
    """Loads the golden eval dataset - the single place this project's
    "known-good" SEO analysis expectations live, same config-as-data
    convention as app/config/agents.yaml.
    """
    data = yaml.safe_load(path.read_text()) or {}
    return [EvalCase.model_validate(raw) for raw in data.get("cases", [])]


def _workflow_from_case(case: EvalCase) -> Workflow:
    now = datetime.now(timezone.utc)
    return Workflow(
        id=uuid.uuid4(),
        repository_url=case.repository_url,
        branch=case.branch,
        goal=case.goal,
        status=WorkflowStatus.RUNNING,
        created_at=now,
        updated_at=now,
    )


async def _execute_capability(
    workflow: Workflow, brief: PlannedCapability, factory: AgentFactory
) -> AgentResult | None:
    """Runs one manager-planned capability directly against the real
    worker - no DB, no Orchestrator retries/persistence. Eval is a
    dev-time tool exercising real agent behavior, not a production
    dispatch, so it doesn't need the machinery that exists for that.
    """
    try:
        worker = factory.create(brief.capability)
    except Exception:
        logger.exception("Eval: no worker registered for capability '%s'", brief.capability)
        return None

    ref = workflow.branch
    now = datetime.now(timezone.utc)
    task = Task(
        id=uuid.uuid4(),
        workflow_id=workflow.id,
        capability=brief.capability,
        status=TaskStatus.RUNNING,
        input={
            "objective": brief.objective,
            "scope": brief.scope,
            "constraints": brief.constraints,
            "acceptance_criteria": brief.acceptance_criteria,
            "repository_url": workflow.repository_url,
            "ref": ref,
        },
        created_at=now,
        updated_at=now,
    )
    try:
        return await worker.execute(task)
    except Exception:
        logger.exception("Eval: capability '%s' failed to execute", brief.capability)
        return None


async def run_eval_case(case: EvalCase, factory: AgentFactory) -> EvalCaseResult:
    """Runs one golden case through the real SEOManagerAgent and real
    workers (via the real AgentFactory), then scores both trajectory (did
    the manager plan the right capabilities) and output (did the workers
    surface the expected findings) - always through eval_scoring.py, never
    re-implemented here.
    """
    workflow = _workflow_from_case(case)
    manager = factory.create("seo_manager")
    briefs = await manager.plan(workflow)
    planned_capabilities = [b.capability for b in briefs]

    trajectory = score_trajectory(planned_capabilities, case.expected_capabilities)

    results = await asyncio.gather(
        *(_execute_capability(workflow, brief, factory) for brief in briefs)
    )
    all_findings: list[Finding] = [
        finding for result in results if result is not None for finding in result.findings
    ]

    output = score_output(all_findings, case.expected_findings)
    score = overall_score(trajectory, output)

    notes: list[str] = []
    if trajectory.missing:
        notes.append(f"Manager did not plan expected capabilities: {trajectory.missing}")
    if trajectory.extra:
        notes.append(f"Manager planned unexpected capabilities: {trajectory.extra}")
    if output.missing:
        notes.append(f"Expected findings not surfaced: {output.missing}")

    return EvalCaseResult(case_id=case.id, trajectory=trajectory, output=output, overall_score=score, notes=notes)


async def run_eval_suite(cases: list[EvalCase], factory: AgentFactory) -> EvalRunSummary:
    """Runs every case concurrently (no shared DB session here - unlike
    run_seo_analysis's live dispatch path, eval touches no database at
    all, so there's no session-sharing hazard to guard against) and
    aggregates one overall score across the suite.
    """
    case_results = list(await asyncio.gather(*(run_eval_case(case, factory) for case in cases)))
    overall = sum(r.overall_score for r in case_results) / len(case_results) if case_results else 1.0
    return EvalRunSummary(case_results=case_results, overall_score=overall)
