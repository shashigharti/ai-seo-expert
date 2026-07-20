from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

from app.domain.models.token_usage import TokenUsage

OutputT = TypeVar("OutputT", bound=BaseModel)


class ModelResponse(BaseModel, Generic[OutputT]):
    output: OutputT
    usage: TokenUsage
    # The model's thinking-mode reasoning trace (Qwen: DashScope's
    # `reasoning_content`), None when thinking wasn't enabled for the call.
    reasoning: str | None = None


class ModelClient(Protocol):
    """Port: abstracts the underlying LLM provider from agent code.

    docs/architecture.md §6 names this ModelClient; the Qwen Cloud adapter
    (QwenCloudModelClient) is one implementation - a different provider could
    implement this same port without agents changing.
    """

    async def run(
        self,
        system_prompt: str,
        user_prompt: str,
        output_type: type[OutputT],
        model: str,
        thinking: bool = False,
    ) -> ModelResponse[OutputT]: ...
