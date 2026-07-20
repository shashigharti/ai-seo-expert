import asyncio
import uuid
from datetime import datetime, timezone

from app.adapters.events.sse_publisher import sse_event_publisher
from app.adapters.postgres.database import SessionLocal
from app.adapters.postgres.repositories.memory_repository import PostgresMemoryRepository
from app.adapters.postgres.repositories.result_repository import PostgresResultRepository
from app.adapters.postgres.repositories.task_repository import PostgresTaskRepository
from app.adapters.postgres.repositories.workflow_repository import PostgresWorkflowRepository
from app.adapters.qwen.model_client import QwenCloudModelClient
from app.agents.bootstrap import build_agent_factory
from app.agents.reviewers.reviewer_agent import needs_review
from app.application.memory.service import MemoryService
from app.application.orchestrator.agent_executor_adapter import AgentTaskExecutorAdapter
from app.application.orchestrator.orchestrator import Orchestrator
from app.application.validation.duplicate_detector import deduplicate_findings
from app.application.validation.evidence_validator import partition_by_evidence
from app.application.validation.schema_validator import validate_agent_result
from app.config.logging import get_logger
from app.config.settings import settings
from app.domain.enums.task_status import TaskStatus
from app.domain.enums.workflow_status import WorkflowStatus
from app.domain.errors import user_facing_message
from app.domain.models.agent_result import AgentResult
from app.domain.models.stored_finding import StoredFinding
from app.domain.models.task import Task
from app.domain.models.task_brief import TaskBrief

logger = get_logger(__name__)

# Which reviewer handles a given worker capability's low-confidence findings
# (docs/agent-architecture.md §1 Reviewer Agents).
_REVIEWER_BY_CAPABILITY = {
    "technical_seo": "technical_seo_reviewer",
    "metadata": "content_reviewer",
    "content_seo": "content_reviewer",
}
_DEFAULT_REVIEWER = "general_seo_reviewer"

# Capabilities dispatch concurrently (see _dispatch_capability), each making
# its own real Qwen Cloud call - capped rather than left unbounded (all 5
# at once previously) to reduce how often that concurrent burst itself
# triggers a 429 that then needs Orchestrator.dispatch's retry loop.
_MAX_CONCURRENT_CAPABILITY_DISPATCHES = 3

# Orchestrator's own default (30s) is sized for whichever model a
# capability's policy points at in app/config/agents.yaml - that's not
# fixed to one tier (economical/balanced/advanced can all point at
# different models, and have at different times), so a single capability
# call can legitimately take longer than 30s depending on which model is
# actually configured. A real run confirmed attempts genuinely timing out
# (asyncio.TimeoutError, logging as an empty message) well before
# finishing once a heavier/slower model was in use for these policies.
#
# 90s (this constant's first value) still wasn't enough once qwen-max +
# thinking: true (balanced policy, e.g. accessibility) became the norm
# rather than the exception - a real run logged 3 consecutive attempts at
# ~91s each, all timing out right at that boundary. qwen-max's thinking
# mode genuinely produces long reasoning traces (2000+ chars / ~500-700
# reasoning tokens observed live) at a larger model's generation speed, so
# this needs real headroom above the typical case, not a value tuned to
# just barely cover it.
_CAPABILITY_DISPATCH_TIMEOUT_SECONDS = 150.0


async def _dispatch_capability(
    workflow_id: uuid.UUID,
    repository_url: str,
    ref: str,
    brief: TaskBrief,
    factory,
    semaphore: asyncio.Semaphore,
) -> Task | None:
    """Dispatches one manager-planned capability task on its own DB
    session. The manager's planned capabilities are independent of each
    other (docs/agent-architecture.md §1 - none needs another's output),
    so run_seo_analysis runs them concurrently via asyncio.gather (bounded
    by `semaphore`); each gets its own session here because SQLAlchemy's
    AsyncSession isn't safe for concurrent use from multiple coroutines at
    once - unlike the read-only AgentFactory/model client/event publisher,
    which are shared across all of them without issue.

    Returns None (logged) if no worker is registered for the capability.
    """
    try:
        worker = factory.create(brief.capability)
    except Exception:
        logger.exception(
            "Workflow %s: no worker available for capability '%s'", workflow_id, brief.capability
        )
        return None

    async with semaphore, SessionLocal() as session:
        orchestrator = Orchestrator(
            PostgresTaskRepository(session),
            sse_event_publisher,
            timeout_seconds=_CAPABILITY_DISPATCH_TIMEOUT_SECONDS,
        )
        task = await orchestrator.create_task(
            workflow_id=workflow_id,
            capability=brief.capability,
            input={
                "objective": brief.objective,
                "scope": brief.scope,
                "constraints": brief.constraints,
                "acceptance_criteria": brief.acceptance_criteria,
                "repository_url": repository_url,
                "ref": ref,
            },
        )
        return await orchestrator.dispatch(task, AgentTaskExecutorAdapter(worker))


async def run_seo_analysis(workflow_id: uuid.UUID) -> None:
    """Manager plans -> Orchestrator dispatches workers -> results validated,
    deduplicated, reviewed, synthesized -> findings persisted.

    Runs as a background task after workflow creation, per
    docs/architecture.md §7 Main Workflow and §10 Review Flow. Opens its own
    DB session/engine rather than reusing the request's, since background
    tasks outlive the request that spawned them.

    Broad top-level try/except is deliberate: this runs detached from any
    HTTP response, so a failure here (missing QWEN_API_KEY, a transient
    network error, an unregistered capability) must be logged, not raised
    into the void - there is no caller left to handle it. It's also the
    only place that failure reaches the workflow's own persisted status:
    without this, a background-task failure was invisible to the user
    entirely - `Workflow.status` would just stay "pending" forever, whether
    the run failed or is still legitimately in progress. RUNNING is set
    before the manager's first Qwen call (the earliest real failure point);
    COMPLETED only on a clean run through the whole function; FAILED (with
    a curated, user-safe error_message - see `user_facing_message`) from the
    except block below, using a fresh session since the one above may
    already be rolled back by the time an exception reaches here.
    """
    model_client = QwenCloudModelClient(api_key=settings.qwen_api_key, base_url=settings.qwen_base_url)
    factory = build_agent_factory(model_client)

    try:
        async with SessionLocal() as session:
            workflow_repository = PostgresWorkflowRepository(session)
            workflow = await workflow_repository.get(workflow_id)
            if workflow is None:
                logger.warning("run_seo_analysis: workflow %s not found", workflow_id)
                return

            workflow = await workflow_repository.update(
                workflow.model_copy(update={"status": WorkflowStatus.RUNNING})
            )

            memory_service = MemoryService(PostgresMemoryRepository(session))

            manager = factory.create("seo_manager")
            memory_context = await memory_service.get_context_for_planning(workflow.repository_url)
            briefs = await manager.plan(workflow, memory_context=memory_context)
            logger.info("Workflow %s: manager planned %d task(s)", workflow_id, len(briefs))

            semaphore = asyncio.Semaphore(_MAX_CONCURRENT_CAPABILITY_DISPATCHES)
            dispatched = await asyncio.gather(
                *(
                    _dispatch_capability(
                        workflow.id, workflow.repository_url, workflow.branch, brief, factory, semaphore
                    )
                    for brief in briefs
                ),
                return_exceptions=True,
            )

            completed_tasks: list[Task] = []
            for brief, result in zip(briefs, dispatched):
                if isinstance(result, Exception):
                    logger.error(
                        "Workflow %s: dispatch failed for capability '%s': %s",
                        workflow_id,
                        brief.capability,
                        result,
                    )
                    continue
                if result is not None and result.status == TaskStatus.COMPLETED:
                    completed_tasks.append(result)

            logger.info(
                "Workflow %s: %d/%d task(s) completed", workflow_id, len(completed_tasks), len(briefs)
            )

            stored = await _review_and_persist(
                session, workflow_id, workflow.repository_url, completed_tasks, factory, memory_service
            )
            logger.info("Workflow %s: %d finding(s) persisted after review", workflow_id, len(stored))

            await workflow_repository.update(workflow.model_copy(update={"status": WorkflowStatus.COMPLETED}))
    except Exception as exc:
        logger.exception("run_seo_analysis failed for workflow %s", workflow_id)
        # Best-effort: persisting the failure must never itself raise out of
        # this function (same reasoning as the docstring's top-level catch -
        # there is no caller left to handle it either way).
        try:
            message = user_facing_message(exc)
            async with SessionLocal() as session:
                workflow_repository = PostgresWorkflowRepository(session)
                workflow = await workflow_repository.get(workflow_id)
                if workflow is not None:
                    await workflow_repository.update(
                        workflow.model_copy(update={"status": WorkflowStatus.FAILED, "error_message": message})
                    )
        except Exception:
            logger.exception("run_seo_analysis: failed to persist failure status for workflow %s", workflow_id)


async def _review_and_persist(
    session, workflow_id, repository_url: str, completed_tasks: list[Task], factory, memory_service: MemoryService
) -> list[StoredFinding]:
    """docs/agent-architecture.md §10 Review Flow: Schema Validator ->
    Evidence Validator -> Duplicate Detector -> Reviewer Agent when needed.
    """
    results: list[tuple[Task, AgentResult]] = []
    for task in completed_tasks:
        agent_result = validate_agent_result(task.output or {})
        if agent_result is None:
            logger.warning("Workflow %s: task %s produced an invalid AgentResult", workflow_id, task.id)
            continue
        results.append((task, agent_result))

    all_findings = [finding for _, result in results for finding in result.findings]
    with_evidence, without_evidence = partition_by_evidence(all_findings)
    if without_evidence:
        logger.info(
            "Workflow %s: dropped %d finding(s) lacking sufficient evidence",
            workflow_id,
            len(without_evidence),
        )
    deduplicated = deduplicate_findings(with_evidence)

    to_persist: list[StoredFinding] = []
    for task, agent_result in results:
        for finding in agent_result.findings:
            if finding not in deduplicated:
                continue  # dropped by evidence validation or dedup

            if needs_review(agent_result.confidence):
                reviewer_capability = _REVIEWER_BY_CAPABILITY.get(task.capability, _DEFAULT_REVIEWER)
                try:
                    reviewer = factory.create(reviewer_capability)
                    verdict = await reviewer.review(
                        finding, context=f"Worker: {agent_result.agent_name}, capability: {task.capability}"
                    )
                except Exception:
                    logger.exception(
                        "Workflow %s: review failed for finding '%s', keeping unreviewed",
                        workflow_id,
                        finding.title,
                    )
                    verdict = None

                if verdict is not None:
                    if verdict.verdict == "rejected":
                        await memory_service.record_false_positive(repository_url, finding, verdict.rationale)
                        continue
                    if verdict.finding is not None:
                        finding = verdict.finding

            to_persist.append(
                StoredFinding(
                    id=uuid.uuid4(),
                    workflow_id=workflow_id,
                    task_id=task.id,
                    agent_name=agent_result.agent_name,
                    finding=finding,
                    created_at=datetime.now(timezone.utc),
                )
            )

    if not to_persist:
        return []
    return await PostgresResultRepository(session).save_many(to_persist)
