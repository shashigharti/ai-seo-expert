from app.domain.models.token_usage import TokenUsage

# Deliberately approximate, hardcoded USD-per-1000-tokens rates - NOT a real
# billing/metering integration. docs/specs.md §5 "Cost Transparency" asks
# for "estimated cost", not an exact invoice figure; there is no live
# pricing API call here, and no historical price tracking. Verify against
# Alibaba Cloud Model Studio's current published pricing before treating
# this as anything more than a rough, clearly-labeled estimate in the UI.
PRICING_USD_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "qwen-plus": {"input": 0.0004, "output": 0.0012},
    "qwen-max": {"input": 0.0016, "output": 0.0064},
}


def estimate_cost_usd(model: str | None, token_usage: TokenUsage | None) -> float | None:
    """Rough estimated cost for one model call - returns None (never a
    guessed number) when the model is unrecognized or usage is missing,
    rather than silently defaulting to some other model's rate.
    """
    if model is None or token_usage is None:
        return None
    rates = PRICING_USD_PER_1K_TOKENS.get(model)
    if rates is None:
        return None
    return (
        token_usage.input_tokens / 1000 * rates["input"]
        + token_usage.output_tokens / 1000 * rates["output"]
    )
