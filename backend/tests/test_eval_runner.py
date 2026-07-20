from app.agents.managers.seo_manager import SEOManagerAgent
from app.agents.workers.technical_seo import TechnicalSEOAgent
from app.application.evaluation.eval_runner import run_eval_case, run_eval_suite
from app.domain.models.agent_result import Finding
from app.domain.models.eval_case import EvalCase, ExpectedFinding
from app.domain.models.manager_decision import PlannedCapability, SEOPlanOutput
from app.domain.models.token_usage import TokenUsage
from app.domain.models.worker_output import WorkerOutput
from app.ports.model_client import ModelResponse


class _StubModelClient:
    """Returns a fixed output regardless of prompt content - enough to
    exercise run_eval_case's wiring without a real QWEN_API_KEY.
    """

    def __init__(self, output):
        self._output = output

    async def run(self, system_prompt, user_prompt, output_type, model, thinking=False):
        return ModelResponse(output=self._output, usage=TokenUsage(input_tokens=1, output_tokens=1))


class _StubFactory:
    def __init__(self, manager, workers: dict):
        self._manager = manager
        self._workers = workers

    def create(self, capability: str):
        if capability == "seo_manager":
            return self._manager
        return self._workers[capability]


def _manager_with_plan(plan_output: SEOPlanOutput) -> SEOManagerAgent:
    return SEOManagerAgent(
        name="SEOManagerAgent",
        capability="seo_manager",
        model_client=_StubModelClient(plan_output),
        tools={},
        skill="prompt",
        model="qwen-plus",
    )


def _worker_with_output(output: WorkerOutput) -> TechnicalSEOAgent:
    return TechnicalSEOAgent(
        name="TechnicalSEOAgent",
        capability="technical_seo",
        model_client=_StubModelClient(output),
        tools={},
        skill="prompt",
        model="qwen-plus",
    )


async def test_run_eval_case_gives_a_perfect_score_when_plan_and_findings_match_expectations():
    finding = Finding(
        category="technical_seo",
        severity="medium",
        title="robots.txt disallows everything",
        description="Disallow: / blocks the whole site from crawlers.",
        evidence="robots.txt: Disallow: /",
        recommendation="Remove the blanket disallow rule.",
    )
    plan = SEOPlanOutput(
        capabilities=[
            PlannedCapability(capability="technical_seo", objective="Check crawlability")
        ],
        rationale="Only crawlability is in scope for this goal.",
    )
    factory = _StubFactory(
        manager=_manager_with_plan(plan),
        workers={"technical_seo": _worker_with_output(WorkerOutput(findings=[finding], confidence=0.9))},
    )
    case = EvalCase(
        id="test-case",
        repository_url="https://github.com/example/project",
        goal="Check crawlability",
        expected_capabilities=["technical_seo"],
        expected_findings=[ExpectedFinding(category="technical_seo", keyword="disallow")],
    )

    result = await run_eval_case(case, factory)

    assert result.case_id == "test-case"
    assert result.trajectory.f1 == 1.0
    assert result.output.coverage == 1.0
    assert result.overall_score == 1.0
    assert result.notes == []


async def test_run_eval_case_flags_missing_capability_and_missing_finding():
    plan = SEOPlanOutput(capabilities=[], rationale="Nothing relevant found.")
    factory = _StubFactory(manager=_manager_with_plan(plan), workers={})
    case = EvalCase(
        id="empty-plan",
        repository_url="https://github.com/example/project",
        goal="Check crawlability",
        expected_capabilities=["technical_seo"],
        expected_findings=[ExpectedFinding(category="technical_seo", keyword="disallow")],
    )

    result = await run_eval_case(case, factory)

    assert result.trajectory.missing == ["technical_seo"]
    assert result.output.missing == ["technical_seo:disallow"]
    assert result.overall_score == 0.0
    assert len(result.notes) == 2


async def test_run_eval_case_flags_unexpected_capability_as_extra():
    plan = SEOPlanOutput(
        capabilities=[PlannedCapability(capability="performance", objective="Check performance")],
        rationale="Performance seemed relevant.",
    )
    factory = _StubFactory(
        manager=_manager_with_plan(plan),
        workers={"performance": _worker_with_output(WorkerOutput(findings=[], confidence=0.5))},
    )
    case = EvalCase(
        id="unexpected-capability",
        repository_url="https://github.com/example/project",
        goal="Check crawlability",
        expected_capabilities=["technical_seo"],
        expected_findings=[],
    )

    result = await run_eval_case(case, factory)

    assert result.trajectory.extra == ["performance"]
    assert result.trajectory.missing == ["technical_seo"]
    assert any("unexpected capabilities" in note for note in result.notes)


async def test_run_eval_suite_averages_case_scores():
    perfect_plan = SEOPlanOutput(capabilities=[], rationale="none needed")
    empty_case_factory = _StubFactory(manager=_manager_with_plan(perfect_plan), workers={})

    cases = [
        EvalCase(id="a", repository_url="https://github.com/example/a", goal="g", expected_capabilities=[]),
        EvalCase(id="b", repository_url="https://github.com/example/b", goal="g", expected_capabilities=[]),
    ]

    summary = await run_eval_suite(cases, empty_case_factory)

    assert [r.case_id for r in summary.case_results] == ["a", "b"]
    assert summary.overall_score == 1.0  # both cases have no expectations at all, trivially satisfied
