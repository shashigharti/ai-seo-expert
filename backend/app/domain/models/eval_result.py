from pydantic import BaseModel, Field


class TrajectoryScore(BaseModel):
    """Did the manager choose the right *path* - the right set of worker
    capabilities - for a case's goal, independent of what those workers
    then found. Precision penalizes busywork (planning capabilities the
    case doesn't expect); recall penalizes gaps (expected capabilities the
    manager never planned).
    """

    planned: list[str]
    expected: list[str]
    matched: list[str]
    missing: list[str]
    extra: list[str]
    precision: float
    recall: float
    f1: float


class OutputScore(BaseModel):
    """Did the analysis actually surface the issues a correct run should
    find, regardless of which capability found them. `matched`/`missing`
    entries are `"category:keyword"` labels, for readable reporting.
    """

    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    coverage: float


class EvalCaseResult(BaseModel):
    """One case's scored outcome - trajectory + output + a single combined
    number (see eval_scoring.overall_score), plus human-readable notes on
    what went wrong, if anything.
    """

    case_id: str
    trajectory: TrajectoryScore
    output: OutputScore
    overall_score: float
    notes: list[str] = Field(default_factory=list)


class EvalRunSummary(BaseModel):
    """A full suite run - every case's result plus one aggregate score, the
    number to watch for regressions across a SKILL.md or model change."""

    case_results: list[EvalCaseResult]
    overall_score: float
