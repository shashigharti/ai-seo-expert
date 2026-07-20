import pytest

from app.adapters.sandbox.model_client import SandboxModelClient, SandboxUnsupportedOutputTypeError
from app.domain.models.manager_decision import SEOPlanOutput
from app.domain.models.worker_output import WorkerOutput
from app.domain.models.agent_result import Finding


async def test_sandbox_client_returns_clearly_labeled_plan_output():
    client = SandboxModelClient()

    result = await client.run(
        system_prompt="ignored", user_prompt="ignored", output_type=SEOPlanOutput, model="qwen-plus"
    )

    assert isinstance(result.output, SEOPlanOutput)
    assert "[SANDBOX]" in result.output.rationale
    assert all("[SANDBOX]" in c.objective for c in result.output.capabilities)
    assert result.usage.input_tokens == 0
    assert result.usage.output_tokens == 0


async def test_sandbox_client_returns_clearly_labeled_worker_output():
    client = SandboxModelClient()

    result = await client.run(
        system_prompt="ignored", user_prompt="ignored", output_type=WorkerOutput, model="qwen-plus"
    )

    assert isinstance(result.output, WorkerOutput)
    assert result.output.confidence == 0.0
    assert any("SANDBOX" in limitation for limitation in result.output.limitations)
    assert all(isinstance(f, Finding) and "[SANDBOX]" in f.title for f in result.output.findings)


async def test_sandbox_client_raises_for_unsupported_output_type():
    client = SandboxModelClient()

    class _SomeOtherOutput:
        pass

    with pytest.raises(SandboxUnsupportedOutputTypeError):
        await client.run(
            system_prompt="ignored", user_prompt="ignored", output_type=_SomeOtherOutput, model="qwen-plus"
        )
