"""CLI entrypoint for the golden-repo evaluation suite.

Exercises the real SEOManagerAgent and real workers (via the real
AgentFactory/agents.yaml) against app/config/eval_cases.yaml, scoring both
trajectory (capability planning) and output (finding coverage) through
app/domain/policies/eval_scoring.py - the single source of truth for what
a score means.

By default this calls the real Qwen model and requires a real
QWEN_API_KEY. Pass --sandbox to run against a simulated model client
instead (AGENTS.md "Sandbox Mode Exception") - for testing the eval
harness's own wiring locally, with zero API cost, before a real run.
Sandbox output carries no evaluative signal about real agent behavior; it
only proves the plumbing runs end to end.

Run from backend/: `python -m scripts.run_eval` (or `--sandbox`)
"""

import argparse
import asyncio
from pathlib import Path

from app.adapters.qwen.model_client import QwenCloudModelClient
from app.adapters.sandbox.model_client import SandboxModelClient
from app.agents.bootstrap import build_agent_factory
from app.application.evaluation.eval_runner import load_eval_cases, run_eval_suite
from app.config.settings import settings
from app.ports.model_client import ModelClient

_EVAL_CASES_PATH = Path(__file__).resolve().parent.parent / "app" / "config" / "eval_cases.yaml"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help=(
            "Use a simulated model client instead of real Qwen Cloud. Must be "
            "passed explicitly - sandbox mode is never a silent fallback for "
            "a missing QWEN_API_KEY."
        ),
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()

    model_client: ModelClient
    if args.sandbox:
        print("=" * 72)
        print("SANDBOX MODE - results are SIMULATED, not a real evaluation.")
        print("No real model is called; scores below carry no real signal,")
        print("only proof that planning -> dispatch -> scoring runs end to end.")
        print("=" * 72)
        model_client = SandboxModelClient()
    else:
        if not settings.qwen_api_key:
            raise SystemExit(
                "QWEN_API_KEY is not set - the eval suite calls the real model "
                "by default. Configure it in .env (see docs/deployment.md), or "
                "pass --sandbox to run against simulated output instead."
            )
        model_client = QwenCloudModelClient(api_key=settings.qwen_api_key, base_url=settings.qwen_base_url)

    cases = load_eval_cases(_EVAL_CASES_PATH)
    factory = build_agent_factory(model_client)

    summary = await run_eval_suite(cases, factory)

    for result in summary.case_results:
        print(f"\n[{result.case_id}] overall={result.overall_score:.2f}")
        print(
            f"  trajectory: precision={result.trajectory.precision:.2f} "
            f"recall={result.trajectory.recall:.2f} f1={result.trajectory.f1:.2f} "
            f"(planned={result.trajectory.planned}, expected={result.trajectory.expected})"
        )
        print(f"  output: coverage={result.output.coverage:.2f} matched={result.output.matched}")
        for note in result.notes:
            print(f"  ! {note}")

    print(f"\n=== Overall suite score: {summary.overall_score:.2f} ({len(summary.case_results)} case(s)) ===")
    if args.sandbox:
        print("(SANDBOX MODE - the score above is simulated, not a real evaluation.)")


if __name__ == "__main__":
    asyncio.run(main())
