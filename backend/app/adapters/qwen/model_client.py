import httpx
from pydantic_ai import Agent as PydanticAIAgent, NativeOutput
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ThinkingPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.domain.errors import ExternalErrorKind, ExternalServiceError
from app.domain.models.token_usage import TokenUsage
from app.ports.model_client import ModelResponse, OutputT

_SERVICE = "Qwen Cloud"

# DashScope's own structured-output support differs by model tier even
# though PydanticAI sends the identical request shape either way - verified
# live: qwen-plus's json_schema (NativeOutput) mode needs no special
# prompting, but qwen-max's falls back to its plainer json_object mode
# server-side, which DashScope then rejects unless the prompt literally
# contains the word "json" ("<400> InternalError.Algo.InvalidParameter:
# 'messages' must contain the word 'json' in some form, to use
# 'response_format' of type 'json_object'."). Only added on the NativeOutput
# fallback path below (see _is_tool_choice_thinking_conflict) - it's a
# transport-level requirement of that specific mode, not something every
# call needs.
_JSON_OUTPUT_REMINDER = "\n\nRespond with valid JSON matching the required output schema."


class QwenClientConfigurationError(ExternalServiceError):
    """Raised when Qwen Cloud credentials are missing at call time."""

    def __init__(self, message: str) -> None:
        super().__init__(service=_SERVICE, kind=ExternalErrorKind.AUTH, message=message)


def _is_tool_choice_thinking_conflict(exc: ModelHTTPError) -> bool:
    """True for DashScope's specific "tool_choice isn't allowed in thinking
    mode" rejection - the signal that the default tool-calling structured
    output path needs to fall back to NativeOutput for this call. Detected
    by message content (DashScope has no dedicated error code for it),
    scoped narrowly so it doesn't misfire on some other 400.
    """
    if exc.status_code != 400:
        return False
    message = exc.body.get("message", "") if isinstance(exc.body, dict) else ""
    return "tool_choice" in message and "thinking mode" in message


def _extract_reasoning(result: AgentRunResult) -> str | None:
    """Pulls the model's thinking-mode reasoning trace out of the run
    result, when thinking was enabled and the model actually produced one.
    PydanticAI already parses DashScope's `reasoning_content` response
    field into a ThinkingPart automatically (openai.py's `_process_thinking`)
    - this just collects it rather than leaving it undiscovered inside
    `result.all_messages()`. None when thinking wasn't used (no such part).
    """
    reasoning_segments = [
        part.content
        for message in result.all_messages()
        for part in getattr(message, "parts", [])
        if isinstance(part, ThinkingPart)
    ]
    return "\n\n".join(reasoning_segments) if reasoning_segments else None


def _is_quota_exhausted(exc: ModelHTTPError) -> bool:
    """True for DashScope's free-tier quota exhaustion (`AllocationQuota.
    FreeTierOnly`, seen live: "The free quota has been exhausted. To
    continue accessing the model on a paid basis, please complete your
    payment information...") - a real, distinct condition from an actually
    invalid API key, even though DashScope surfaces both as a 401/403. The
    key is valid; the account just has no quota left, so telling the user
    to "check that it's valid" would be actively misleading.
    """
    if exc.status_code != 403:
        return False
    code = exc.body.get("code", "") if isinstance(exc.body, dict) else ""
    return code == "AllocationQuota.FreeTierOnly"


def _classify_model_http_error(exc: ModelHTTPError) -> ExternalServiceError:
    """Turns a raw PydanticAI ModelHTTPError into a curated, user-safe
    ExternalServiceError - never the raw stringified exception (which
    includes the upstream JSON error body verbatim).
    """
    if _is_quota_exhausted(exc):
        return ExternalServiceError(
            service=_SERVICE,
            kind=ExternalErrorKind.AUTH,
            message=(
                "Qwen Cloud's free-tier quota has been exhausted for this account. Add payment "
                'information in the Alibaba Cloud console, or disable "use free tier only" mode, '
                "to continue."
            ),
        )
    if exc.status_code in (401, 403):
        return ExternalServiceError(
            service=_SERVICE,
            kind=ExternalErrorKind.AUTH,
            message="Qwen Cloud rejected the configured QWEN_API_KEY. Check that it's valid for this account.",
        )
    if exc.status_code == 429:
        return ExternalServiceError(
            service=_SERVICE,
            kind=ExternalErrorKind.RATE_LIMIT,
            message="Qwen Cloud rate limit exceeded. Wait a while before trying again.",
        )
    if exc.status_code == 404:
        return ExternalServiceError(
            service=_SERVICE,
            kind=ExternalErrorKind.NOT_FOUND,
            message="The configured Qwen model was not found. Check QWEN_MODEL.",
        )
    return ExternalServiceError(
        service=_SERVICE,
        kind=ExternalErrorKind.UNKNOWN,
        message="The Qwen Cloud API request failed.",
    )


class QwenCloudModelClient:
    """Adapter implementing the ModelClient port against Qwen Cloud's
    OpenAI-compatible endpoint (DashScope compatible-mode), via PydanticAI.

    docs/architecture.md §6 names this QwenCloudModelClient.
    """

    def __init__(self, api_key: str | None, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url

    async def run(
        self,
        system_prompt: str,
        user_prompt: str,
        output_type: type[OutputT],
        model: str,
        thinking: bool = False,
    ) -> ModelResponse[OutputT]:
        if not self._api_key:
            raise QwenClientConfigurationError(
                "QWEN_API_KEY is not set. Configure it in .env to call Qwen Cloud "
                "- see docs/deployment.md."
            )

        provider = OpenAIProvider(base_url=self._base_url, api_key=self._api_key)
        chat_model = OpenAIChatModel(model, provider=provider)

        # enable_thinking is Qwen-specific, not a standard OpenAI param, so it
        # must be passed via extra_body (per Alibaba Cloud Model Studio docs).
        model_settings = {"extra_body": {"enable_thinking": thinking}} if thinking else None

        # Default: PydanticAIAgent's normal structured-output path (forces
        # tool_choice to call the output schema as a tool). Left as the
        # default rather than always using NativeOutput because it's
        # actually the *more* reliable one for this app's more complex
        # nested schemas on at least one real model (qwen-max) - verified
        # live, NativeOutput sometimes lets qwen-max return a technically-
        # valid but semantically-empty scope for SEOPlanOutput, where the
        # default tool-calling path gets it right consistently.
        agent = PydanticAIAgent(chat_model, output_type=output_type, system_prompt=system_prompt)

        try:
            result = await agent.run(user_prompt, model_settings=model_settings)
        except ModelHTTPError as exc:
            if thinking and _is_tool_choice_thinking_conflict(exc):
                # Some models (verified: qwen-plus, not qwen-max) force
                # tool_choice for the default path regardless of thinking
                # mode, which DashScope's thinking mode rejects outright
                # ("<400> InternalError.Algo.InvalidParameter: The
                # tool_choice parameter does not support being set to
                # required or object in thinking mode"). NativeOutput
                # (response_format/json_schema) sidesteps forced tool_choice
                # entirely - verified live this fixes exactly this case,
                # including this app's real nested/Literal-bearing output
                # schemas. Scoped to only this specific failure so models
                # that already work fine via the default path (qwen-max)
                # are unaffected.
                native_agent = PydanticAIAgent(
                    chat_model,
                    output_type=NativeOutput(output_type),
                    system_prompt=system_prompt + _JSON_OUTPUT_REMINDER,
                )
                try:
                    result = await native_agent.run(user_prompt, model_settings=model_settings)
                except ModelHTTPError as retry_exc:
                    raise _classify_model_http_error(retry_exc) from retry_exc
            else:
                raise _classify_model_http_error(exc) from exc
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ExternalServiceError(
                service=_SERVICE,
                kind=ExternalErrorKind.NETWORK,
                message="Could not reach Qwen Cloud - check your network connection and try again.",
            ) from exc

        return ModelResponse[output_type](
            output=result.output,
            reasoning=_extract_reasoning(result),
            usage=TokenUsage(
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
                reasoning_tokens=(result.usage.details or {}).get("reasoning_tokens"),
            ),
        )
