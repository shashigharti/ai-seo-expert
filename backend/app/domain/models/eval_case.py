from pydantic import BaseModel, Field


class ExpectedFinding(BaseModel):
    """A minimal, matchable expectation for a golden eval case - not a
    full Finding, since exact LLM wording varies run to run. Matching is a
    deterministic category + keyword substring check (see
    app/domain/policies/eval_scoring.py:score_output), not an LLM-as-judge
    call, so scores are reproducible.
    """

    category: str
    keyword: str


class EvalCase(BaseModel):
    """One golden test case for the SEO analysis pipeline: a real
    repository, the capabilities the manager is expected to plan
    (trajectory), and the findings a correct analysis should surface
    (output). This is the single source of truth for what "correct" means
    for a given repository - app/config/eval_cases.yaml is the dataset,
    this model is its schema, and eval_scoring.py is the only place that
    turns a case + real agent output into a score.
    """

    id: str
    repository_url: str
    goal: str
    branch: str = "master"
    expected_capabilities: list[str] = Field(default_factory=list)
    expected_findings: list[ExpectedFinding] = Field(default_factory=list)
