from app.domain.models.agent_result import Finding
from app.domain.models.manager_decision import PlannedCapability, SEOPlanOutput
from app.domain.models.token_usage import TokenUsage
from app.domain.models.worker_output import WorkerOutput
from app.ports.model_client import ModelResponse, OutputT


class SandboxUnsupportedOutputTypeError(Exception):
    pass


class SandboxModelClient:
    """AGENTS.md "Sandbox Mode Exception": a ModelClient implementation that
    never calls a real model. Only ever constructed explicitly (see
    scripts/run_eval.py's `--sandbox` flag) - never a silent fallback for a
    missing QWEN_API_KEY - and exists to exercise the eval harness's own
    wiring (does planning->dispatch->scoring actually run end to end)
    locally, with zero API cost and no real credential, before a real run.

    Every returned value is deterministic and unmistakably simulated (titled
    "[SANDBOX] ..." throughout, zero confidence, a limitation stating
    plainly that this is not real output) so it can never be mistaken for a
    genuine analysis result. It carries no evaluative signal about whether
    the real model plans or finds things correctly - only that the plumbing
    around it doesn't crash.

    Only the two output types the eval path actually requests
    (SEOPlanOutput for the manager, WorkerOutput for workers) are supported;
    an unrecognized output_type raises rather than guessing at a fabricated
    schema.
    """

    async def run(
        self,
        system_prompt: str,
        user_prompt: str,
        output_type: type[OutputT],
        model: str,
        thinking: bool = False,
    ) -> ModelResponse[OutputT]:
        if output_type is SEOPlanOutput:
            output = SEOPlanOutput(
                capabilities=[
                    PlannedCapability(
                        capability="technical_seo",
                        objective="[SANDBOX] Simulated objective - no real planning occurred.",
                        scope={"files": []},
                        constraints=[],
                        acceptance_criteria=["[SANDBOX] simulated acceptance criterion"],
                        priority="medium",
                    )
                ],
                rationale="[SANDBOX] Simulated rationale - no real model was called.",
            )
        elif output_type is WorkerOutput:
            output = WorkerOutput(
                findings=[
                    Finding(
                        category="sandbox",
                        severity="low",
                        title="[SANDBOX] Example finding - not a real analysis result",
                        description="Simulated output from sandbox mode; no real model call was made.",
                        evidence="[SANDBOX] simulated evidence",
                        recommendation="[SANDBOX] simulated recommendation",
                    )
                ],
                confidence=0.0,
                limitations=["SANDBOX MODE: this output is simulated, not a real analysis."],
                follow_up_suggestions=[],
            )
        else:
            raise SandboxUnsupportedOutputTypeError(
                f"Sandbox mode has no simulated response for output_type="
                f"{getattr(output_type, '__name__', output_type)!r}; add a case in "
                "SandboxModelClient.run() or run with a real QWEN_API_KEY instead."
            )

        return ModelResponse(output=output, usage=TokenUsage(input_tokens=0, output_tokens=0))
