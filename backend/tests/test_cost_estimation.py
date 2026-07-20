from app.domain.models.token_usage import TokenUsage
from app.domain.policies.cost_estimation import estimate_cost_usd


def test_estimate_cost_usd_known_model():
    usage = TokenUsage(input_tokens=1000, output_tokens=1000)
    cost = estimate_cost_usd("qwen-plus", usage)

    assert cost == 0.0004 + 0.0012


def test_estimate_cost_usd_unknown_model_returns_none():
    usage = TokenUsage(input_tokens=1000, output_tokens=1000)
    assert estimate_cost_usd("some-other-model", usage) is None


def test_estimate_cost_usd_missing_usage_returns_none():
    assert estimate_cost_usd("qwen-plus", None) is None


def test_estimate_cost_usd_missing_model_returns_none():
    usage = TokenUsage(input_tokens=1000, output_tokens=1000)
    assert estimate_cost_usd(None, usage) is None
