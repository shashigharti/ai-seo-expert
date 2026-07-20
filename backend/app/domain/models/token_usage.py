from pydantic import BaseModel


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    # Subset of output_tokens spent on thinking-mode reasoning (not
    # additive - DashScope bills reasoning as part of output_tokens, this
    # is a breakdown of it), None when thinking wasn't enabled for the call.
    reasoning_tokens: int | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
