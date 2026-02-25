"""Tests for the LLM client abstraction layer.

Covers:
- Provider selection (anthropic vs vllm)
- Anthropic API call format (headers, payload)
- vLLM API call format (OpenAI-compatible)
- Default token handling
- Unknown provider error
- close() method
"""

from __future__ import annotations

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from config import LLMConfig
from llm_client import LLMClient

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Config selection tests
# ---------------------------------------------------------------------------
class TestConfigSelection:
    """Tests for provider configuration."""

    def test_anthropic_config(self, llm_config):
        client = LLMClient(llm_config)
        assert client.config.provider == "anthropic"
        assert client.config.model == "claude-sonnet-4-20250514"
        assert client.config.api_key == "test-api-key-not-real"

    def test_vllm_config(self, vllm_config):
        client = LLMClient(vllm_config)
        assert client.config.provider == "vllm"
        assert client.config.vllm_endpoint == "http://localhost:8000"

    def test_default_token_limits(self, llm_config):
        assert llm_config.generator_max_tokens == 8192
        assert llm_config.reviewer_max_tokens == 16384

    def test_reviewer_tokens_are_2x_generator(self, llm_config):
        assert llm_config.reviewer_max_tokens == 2 * llm_config.generator_max_tokens


# ---------------------------------------------------------------------------
# generate() provider routing tests
# ---------------------------------------------------------------------------
class TestGenerateRouting:
    """Tests for the generate method's provider routing."""

    @pytest.mark.asyncio
    async def test_routes_to_anthropic(self, llm_config):
        client = LLMClient(llm_config)
        client._call_anthropic = AsyncMock(return_value="anthropic response")
        client._call_vllm = AsyncMock(return_value="vllm response")

        result = await client.generate("system", "user")
        assert result == "anthropic response"
        client._call_anthropic.assert_awaited_once()
        client._call_vllm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_routes_to_vllm(self, vllm_config):
        client = LLMClient(vllm_config)
        client._call_anthropic = AsyncMock(return_value="anthropic response")
        client._call_vllm = AsyncMock(return_value="vllm response")

        result = await client.generate("system", "user")
        assert result == "vllm response"
        client._call_vllm.assert_awaited_once()
        client._call_anthropic.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unknown_provider_raises_value_error(self):
        config = LLMConfig(
            provider="unknown_provider",
            model="some-model",
            api_key="key",
            vllm_endpoint="http://localhost:8000",
        )
        client = LLMClient(config)

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            await client.generate("system", "user")

    @pytest.mark.asyncio
    async def test_default_max_tokens_used_when_none(self, llm_config):
        client = LLMClient(llm_config)
        client._call_anthropic = AsyncMock(return_value="response")

        await client.generate("system", "user", max_tokens=None)

        call_args = client._call_anthropic.call_args
        # Should use generator_max_tokens as default
        assert call_args[0][2] == llm_config.generator_max_tokens  # third positional arg

    @pytest.mark.asyncio
    async def test_explicit_max_tokens_used(self, llm_config):
        client = LLMClient(llm_config)
        client._call_anthropic = AsyncMock(return_value="response")

        await client.generate("system", "user", max_tokens=2048)

        call_args = client._call_anthropic.call_args
        assert call_args[0][2] == 2048

    @pytest.mark.asyncio
    async def test_temperature_forwarded(self, llm_config):
        client = LLMClient(llm_config)
        client._call_anthropic = AsyncMock(return_value="response")

        await client.generate("system", "user", temperature=0.7)

        call_args = client._call_anthropic.call_args
        assert call_args[0][3] == 0.7  # fourth positional arg


# ---------------------------------------------------------------------------
# Anthropic API call tests (mocked httpx)
# ---------------------------------------------------------------------------
class TestCallAnthropic:
    """Tests for the _call_anthropic method."""

    @pytest.mark.asyncio
    async def test_correct_endpoint(self, llm_config):
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"text": "generated code"}]}
        mock_response.raise_for_status = MagicMock()

        client = LLMClient(llm_config)
        client._http = AsyncMock()
        client._http.post = AsyncMock(return_value=mock_response)

        result = await client._call_anthropic("system prompt", "user msg", 4096, 0.3)

        assert result == "generated code"
        call_args = client._http.post.call_args
        assert call_args[0][0] == "https://api.anthropic.com/v1/messages"

    @pytest.mark.asyncio
    async def test_correct_headers(self, llm_config):
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"text": "ok"}]}
        mock_response.raise_for_status = MagicMock()

        client = LLMClient(llm_config)
        client._http = AsyncMock()
        client._http.post = AsyncMock(return_value=mock_response)

        await client._call_anthropic("sys", "usr", 4096, 0.3)

        call_kwargs = client._http.post.call_args[1]
        headers = call_kwargs["headers"]
        assert headers["x-api-key"] == "test-api-key-not-real"
        assert headers["anthropic-version"] == "2023-06-01"
        assert headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_correct_payload(self, llm_config):
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": [{"text": "ok"}]}
        mock_response.raise_for_status = MagicMock()

        client = LLMClient(llm_config)
        client._http = AsyncMock()
        client._http.post = AsyncMock(return_value=mock_response)

        await client._call_anthropic("my system", "my user", 8192, 0.5)

        call_kwargs = client._http.post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["model"] == "claude-sonnet-4-20250514"
        assert payload["max_tokens"] == 8192
        assert payload["temperature"] == 0.5
        assert payload["system"] == "my system"
        assert payload["messages"] == [{"role": "user", "content": "my user"}]


# ---------------------------------------------------------------------------
# vLLM API call tests (mocked httpx)
# ---------------------------------------------------------------------------
class TestCallVllm:
    """Tests for the _call_vllm method."""

    @pytest.mark.asyncio
    async def test_correct_endpoint(self, vllm_config):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "vllm output"}}]
        }
        mock_response.raise_for_status = MagicMock()

        client = LLMClient(vllm_config)
        client._http = AsyncMock()
        client._http.post = AsyncMock(return_value=mock_response)

        result = await client._call_vllm("system", "user", 4096, 0.3)

        assert result == "vllm output"
        call_args = client._http.post.call_args
        assert call_args[0][0] == "http://localhost:8000/v1/chat/completions"

    @pytest.mark.asyncio
    async def test_correct_payload_format(self, vllm_config):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "output"}}]
        }
        mock_response.raise_for_status = MagicMock()

        client = LLMClient(vllm_config)
        client._http = AsyncMock()
        client._http.post = AsyncMock(return_value=mock_response)

        await client._call_vllm("sys prompt", "usr msg", 2048, 0.1)

        call_kwargs = client._http.post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["model"] == "qwen2.5-coder-7b"
        assert payload["max_tokens"] == 2048
        assert payload["temperature"] == 0.1
        assert payload["messages"] == [
            {"role": "system", "content": "sys prompt"},
            {"role": "user", "content": "usr msg"},
        ]


# ---------------------------------------------------------------------------
# close() tests
# ---------------------------------------------------------------------------
class TestClose:
    """Tests for cleanup."""

    @pytest.mark.asyncio
    async def test_close_calls_aclose(self, llm_config):
        client = LLMClient(llm_config)
        client._http = AsyncMock()
        client._http.aclose = AsyncMock()

        await client.close()
        client._http.aclose.assert_awaited_once()
