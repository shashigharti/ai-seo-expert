from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel
from pydantic_ai import NativeOutput
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import TextPart, ThinkingPart

from app.adapters.qwen.model_client import (
    QwenClientConfigurationError,
    QwenCloudModelClient,
    _JSON_OUTPUT_REMINDER,
    _is_quota_exhausted,
    _is_tool_choice_thinking_conflict,
)
from app.domain.errors import ExternalErrorKind, ExternalServiceError


class _StubFindings(BaseModel):
    summary: str


async def test_run_raises_when_api_key_is_missing():
    client = QwenCloudModelClient(api_key=None, base_url="https://example.com/v1")

    with pytest.raises(QwenClientConfigurationError):
        await client.run(
            system_prompt="You are an SEO auditor.",
            user_prompt="Audit this page.",
            output_type=_StubFindings,
            model="qwen-plus",
        )


async def test_run_delegates_to_pydantic_ai_with_expected_arguments():
    fake_usage = MagicMock(input_tokens=120, output_tokens=45)
    fake_result = MagicMock(output=_StubFindings(summary="looks fine"), usage=fake_usage)

    with (
        patch("app.adapters.qwen.model_client.OpenAIProvider") as mock_provider_cls,
        patch("app.adapters.qwen.model_client.OpenAIChatModel") as mock_model_cls,
        patch("app.adapters.qwen.model_client.PydanticAIAgent") as mock_agent_cls,
    ):
        mock_agent_instance = mock_agent_cls.return_value
        mock_agent_instance.run = AsyncMock(return_value=fake_result)

        client = QwenCloudModelClient(api_key="test-key", base_url="https://dashscope.example/v1")
        response = await client.run(
            system_prompt="You are an SEO auditor.",
            user_prompt="Audit this page.",
            output_type=_StubFindings,
            model="qwen-plus",
            thinking=True,
        )

    mock_provider_cls.assert_called_once_with(base_url="https://dashscope.example/v1", api_key="test-key")
    mock_model_cls.assert_called_once_with("qwen-plus", provider=mock_provider_cls.return_value)
    # The default path (bare output_type, plain system_prompt) is used
    # first - no NativeOutput/JSON-reminder unless that specific call
    # actually hits the tool_choice/thinking conflict (see the fallback
    # tests below). Most models (verified live: qwen-max) never do, and
    # are actually *more* reliable on this app's complex nested schemas via
    # this default path, so it must stay the first thing tried.
    mock_agent_cls.assert_called_once_with(
        mock_model_cls.return_value,
        output_type=_StubFindings,
        system_prompt="You are an SEO auditor.",
    )
    mock_agent_instance.run.assert_awaited_once_with(
        "Audit this page.", model_settings={"extra_body": {"enable_thinking": True}}
    )

    assert response.output.summary == "looks fine"
    assert response.usage.input_tokens == 120
    assert response.usage.output_tokens == 45
    assert response.usage.total_tokens == 165


async def test_run_extracts_reasoning_trace_and_reasoning_tokens_when_thinking_produced_one():
    """PydanticAI parses DashScope's `reasoning_content` response field into
    a ThinkingPart automatically (openai.py's `_process_thinking`) - this
    confirms QwenCloudModelClient actually surfaces it rather than leaving
    it stranded in result.all_messages(), and pulls reasoning_tokens out of
    usage.details the same way.
    """
    fake_usage = MagicMock(input_tokens=30, output_tokens=850, details={"reasoning_tokens": 687})
    fake_message = MagicMock(
        parts=[
            ThinkingPart(content="Let me think about how to approach this."),
            TextPart(content='{"summary": "looks fine"}'),
        ]
    )
    fake_result = MagicMock(
        output=_StubFindings(summary="looks fine"),
        usage=fake_usage,
        all_messages=MagicMock(return_value=[fake_message]),
    )

    with (
        patch("app.adapters.qwen.model_client.OpenAIProvider"),
        patch("app.adapters.qwen.model_client.OpenAIChatModel"),
        patch("app.adapters.qwen.model_client.PydanticAIAgent") as mock_agent_cls,
    ):
        mock_agent_cls.return_value.run = AsyncMock(return_value=fake_result)

        client = QwenCloudModelClient(api_key="test-key", base_url="https://dashscope.example/v1")
        response = await client.run(
            system_prompt="sys", user_prompt="usr", output_type=_StubFindings, model="qwen-plus", thinking=True
        )

    assert response.reasoning == "Let me think about how to approach this."
    assert response.usage.reasoning_tokens == 687


async def test_run_omits_model_settings_when_thinking_is_disabled():
    fake_result = MagicMock(output=_StubFindings(summary="ok"), usage=MagicMock(input_tokens=1, output_tokens=1))

    with (
        patch("app.adapters.qwen.model_client.OpenAIProvider"),
        patch("app.adapters.qwen.model_client.OpenAIChatModel"),
        patch("app.adapters.qwen.model_client.PydanticAIAgent") as mock_agent_cls,
    ):
        mock_agent_cls.return_value.run = AsyncMock(return_value=fake_result)

        client = QwenCloudModelClient(api_key="test-key", base_url="https://dashscope.example/v1")
        await client.run(
            system_prompt="sys",
            user_prompt="usr",
            output_type=_StubFindings,
            model="qwen-plus",
            thinking=False,
        )

    mock_agent_cls.return_value.run.assert_awaited_once_with("usr", model_settings=None)
    mock_agent_cls.assert_called_once_with(
        mock_agent_cls.call_args.args[0], output_type=_StubFindings, system_prompt="sys"
    )


def test_is_tool_choice_thinking_conflict_matches_the_real_dashscope_message():
    exc = ModelHTTPError(
        status_code=400,
        model_name="qwen-plus",
        body={
            "message": (
                "<400> InternalError.Algo.InvalidParameter: The tool_choice parameter does not "
                "support being set to required or object in thinking mode"
            )
        },
    )
    assert _is_tool_choice_thinking_conflict(exc) is True


@pytest.mark.parametrize(
    "status_code,body",
    [
        (400, {"message": "'messages' must contain the word 'json'"}),  # different 400, unrelated
        (401, {"message": "Incorrect API key"}),
        (400, {}),
        (400, None),
    ],
)
def test_is_tool_choice_thinking_conflict_does_not_misfire(status_code, body):
    exc = ModelHTTPError(status_code=status_code, model_name="qwen-plus", body=body)
    assert _is_tool_choice_thinking_conflict(exc) is False


def _tool_choice_thinking_error(model_name: str = "qwen-plus") -> ModelHTTPError:
    return ModelHTTPError(
        status_code=400,
        model_name=model_name,
        body={
            "message": (
                "<400> InternalError.Algo.InvalidParameter: The tool_choice parameter does not "
                "support being set to required or object in thinking mode"
            )
        },
    )


async def test_run_falls_back_to_native_output_on_tool_choice_thinking_conflict():
    fake_result = MagicMock(output=_StubFindings(summary="ok"), usage=MagicMock(input_tokens=1, output_tokens=1))
    default_agent = MagicMock()
    default_agent.run = AsyncMock(side_effect=_tool_choice_thinking_error())
    native_agent = MagicMock()
    native_agent.run = AsyncMock(return_value=fake_result)

    with (
        patch("app.adapters.qwen.model_client.OpenAIProvider"),
        patch("app.adapters.qwen.model_client.OpenAIChatModel"),
        patch("app.adapters.qwen.model_client.PydanticAIAgent") as mock_agent_cls,
    ):
        mock_agent_cls.side_effect = [default_agent, native_agent]

        client = QwenCloudModelClient(api_key="test-key", base_url="https://dashscope.example/v1")
        response = await client.run(
            system_prompt="sys", user_prompt="usr", output_type=_StubFindings, model="qwen-plus", thinking=True
        )

    assert response.output.summary == "ok"
    default_agent.run.assert_awaited_once()
    native_agent.run.assert_awaited_once()
    # The retry agent must use NativeOutput + the JSON reminder - see
    # model_client.py's comment on why both are needed for this fallback
    # specifically (not the default path).
    _, kwargs = mock_agent_cls.call_args_list[1]
    assert kwargs["output_type"] == NativeOutput(_StubFindings)
    assert kwargs["system_prompt"] == "sys" + _JSON_OUTPUT_REMINDER


async def test_run_does_not_fall_back_when_thinking_is_disabled():
    """The exact tool_choice/thinking conflict error shouldn't occur with
    thinking disabled in practice, but confirms the guard is on `thinking`,
    not just the error shape - a real, different 400 shouldn't accidentally
    trigger a retry."""
    with patch("app.adapters.qwen.model_client.PydanticAIAgent") as mock_agent_cls:
        mock_agent_cls.return_value.run = AsyncMock(side_effect=_tool_choice_thinking_error())
        client = QwenCloudModelClient(api_key="test-key", base_url="https://dashscope.example/v1")

        with pytest.raises(ExternalServiceError) as exc_info:
            await client.run(
                system_prompt="sys", user_prompt="usr", output_type=_StubFindings, model="qwen-plus", thinking=False
            )

    assert exc_info.value.kind == ExternalErrorKind.UNKNOWN
    mock_agent_cls.assert_called_once()  # no retry agent constructed


async def test_run_reraises_classified_error_when_native_output_retry_also_fails():
    default_agent = MagicMock()
    default_agent.run = AsyncMock(side_effect=_tool_choice_thinking_error())
    native_agent = MagicMock()
    native_agent.run = AsyncMock(
        side_effect=ModelHTTPError(status_code=401, model_name="qwen-plus", body={"message": "bad key"})
    )

    with patch("app.adapters.qwen.model_client.PydanticAIAgent") as mock_agent_cls:
        mock_agent_cls.side_effect = [default_agent, native_agent]
        client = QwenCloudModelClient(api_key="test-key", base_url="https://dashscope.example/v1")

        with pytest.raises(ExternalServiceError) as exc_info:
            await client.run(
                system_prompt="sys", user_prompt="usr", output_type=_StubFindings, model="qwen-plus", thinking=True
            )

    assert exc_info.value.kind == ExternalErrorKind.AUTH


def test_is_quota_exhausted_matches_the_real_dashscope_response():
    """Real response body, verified live against a Qwen Cloud account whose
    free-tier quota had run out (this project's own account, mid-session)."""
    exc = ModelHTTPError(
        status_code=403,
        model_name="qwen-plus",
        body={
            "message": (
                "The free quota has been exhausted. To continue accessing the model on a paid "
                'basis, please complete your payment information (or disable the "use free tier '
                'only" mode in the management console if already completed).'
            ),
            "type": "AllocationQuota.FreeTierOnly",
            "param": None,
            "code": "AllocationQuota.FreeTierOnly",
        },
    )
    assert _is_quota_exhausted(exc) is True


@pytest.mark.parametrize(
    "status_code,body",
    [
        (401, {"message": "Incorrect API key provided", "code": "invalid_api_key"}),
        (403, {"message": "Forbidden", "code": "AccessDenied"}),
        (403, None),
    ],
)
def test_is_quota_exhausted_does_not_misfire(status_code, body):
    exc = ModelHTTPError(status_code=status_code, model_name="qwen-plus", body=body)
    assert _is_quota_exhausted(exc) is False


async def test_run_classifies_quota_exhaustion_with_a_distinct_message_from_an_invalid_key():
    with patch("app.adapters.qwen.model_client.PydanticAIAgent") as mock_agent_cls:
        mock_agent_cls.return_value.run = AsyncMock(
            side_effect=ModelHTTPError(
                status_code=403,
                model_name="qwen-plus",
                body={"message": "The free quota has been exhausted.", "code": "AllocationQuota.FreeTierOnly"},
            )
        )
        client = QwenCloudModelClient(api_key="test-key", base_url="https://dashscope.example/v1")

        with pytest.raises(ExternalServiceError) as exc_info:
            await client.run(
                system_prompt="sys", user_prompt="usr", output_type=_StubFindings, model="qwen-plus"
            )

    assert exc_info.value.kind == ExternalErrorKind.AUTH
    assert "quota" in exc_info.value.message.lower()
    assert "check that it's valid" not in exc_info.value.message.lower()


async def test_run_classifies_401_as_auth():
    with patch("app.adapters.qwen.model_client.PydanticAIAgent") as mock_agent_cls:
        mock_agent_cls.return_value.run = AsyncMock(
            side_effect=ModelHTTPError(status_code=401, model_name="qwen-plus", body={"message": "Incorrect API key"})
        )
        client = QwenCloudModelClient(api_key="bad-key", base_url="https://dashscope.example/v1")

        with pytest.raises(ExternalServiceError) as exc_info:
            await client.run(
                system_prompt="sys", user_prompt="usr", output_type=_StubFindings, model="qwen-plus"
            )

    assert exc_info.value.kind == ExternalErrorKind.AUTH
    assert "Incorrect API key" not in exc_info.value.message


async def test_run_classifies_429_as_rate_limit():
    with patch("app.adapters.qwen.model_client.PydanticAIAgent") as mock_agent_cls:
        mock_agent_cls.return_value.run = AsyncMock(
            side_effect=ModelHTTPError(status_code=429, model_name="qwen-plus", body={"message": "Rate limited"})
        )
        client = QwenCloudModelClient(api_key="test-key", base_url="https://dashscope.example/v1")

        with pytest.raises(ExternalServiceError) as exc_info:
            await client.run(
                system_prompt="sys", user_prompt="usr", output_type=_StubFindings, model="qwen-plus"
            )

    assert exc_info.value.kind == ExternalErrorKind.RATE_LIMIT


async def test_run_classifies_network_error():
    with patch("app.adapters.qwen.model_client.PydanticAIAgent") as mock_agent_cls:
        mock_agent_cls.return_value.run = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        client = QwenCloudModelClient(api_key="test-key", base_url="https://dashscope.example/v1")

        with pytest.raises(ExternalServiceError) as exc_info:
            await client.run(
                system_prompt="sys", user_prompt="usr", output_type=_StubFindings, model="qwen-plus"
            )

    assert exc_info.value.kind == ExternalErrorKind.NETWORK
    assert "connection refused" not in exc_info.value.message
