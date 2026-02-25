"""Tests for the Code Generator Agent.

Covers:
- Message construction (system prompt, user message)
- Code fence stripping
- Language detection (VB.NET vs C#)
- Retry feedback inclusion
- Few-shot example truncation
- Integration with LLM client (mocked)
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from agents.code_generator import (
    GenerationRequest,
    GenerationResult,
    TargetRuntime,
    _build_user_message,
    _load_system_prompt,
    generate_code,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _build_user_message tests
# ---------------------------------------------------------------------------
class TestBuildUserMessage:
    """Tests for the user message construction helper."""

    def _make_request(self, **overrides) -> GenerationRequest:
        defaults = dict(
            requirement="Calculate consolidation elimination entries",
            rule_type="Finance Business Rule",
            target_runtime=TargetRuntime.NET8,
            project_context={"dimension": "Entity", "scenario": "Actual"},
            few_shot_examples=[],
            retry_feedback="",
        )
        defaults.update(overrides)
        return GenerationRequest(**defaults)

    def test_includes_requirement(self):
        req = self._make_request()
        msg = _build_user_message(req)
        assert "## Requirement" in msg
        assert "Calculate consolidation elimination entries" in msg

    def test_includes_rule_type(self):
        req = self._make_request(rule_type="Data Management")
        msg = _build_user_message(req)
        assert "## Rule Type" in msg
        assert "Data Management" in msg

    def test_includes_target_runtime(self):
        req = self._make_request(target_runtime=TargetRuntime.NET48)
        msg = _build_user_message(req)
        assert "net48" in msg

    def test_includes_project_context(self):
        req = self._make_request(project_context={"env": "Production", "region": "US"})
        msg = _build_user_message(req)
        assert "## Project Context" in msg
        assert "env: Production" in msg
        assert "region: US" in msg

    def test_empty_project_context_omitted(self):
        req = self._make_request(project_context={})
        msg = _build_user_message(req)
        assert "## Project Context" not in msg

    def test_few_shot_examples_included(self):
        examples = ["Example A code", "Example B code"]
        req = self._make_request(few_shot_examples=examples)
        msg = _build_user_message(req)
        assert "## Reference Examples" in msg
        assert "Example A code" in msg
        assert "Example B code" in msg

    def test_few_shot_examples_truncated_to_three(self):
        examples = [f"Example {i}" for i in range(5)]
        req = self._make_request(few_shot_examples=examples)
        msg = _build_user_message(req)
        assert "Example 0" in msg
        assert "Example 2" in msg
        # The 4th and 5th examples should be excluded
        assert "Example 3" not in msg
        assert "Example 4" not in msg

    def test_retry_feedback_included(self):
        req = self._make_request(retry_feedback="Missing Try/Catch block")
        msg = _build_user_message(req)
        assert "## Previous Review Feedback" in msg
        assert "Missing Try/Catch block" in msg

    def test_no_retry_feedback_when_empty(self):
        req = self._make_request(retry_feedback="")
        msg = _build_user_message(req)
        assert "## Previous Review Feedback" not in msg

    def test_instructions_always_present(self):
        req = self._make_request()
        msg = _build_user_message(req)
        assert "## Instructions" in msg
        assert "Return ONLY the source code" in msg


# ---------------------------------------------------------------------------
# _load_system_prompt tests
# ---------------------------------------------------------------------------
class TestLoadSystemPrompt:
    """Tests for system prompt loading and customization."""

    def test_net8_prompt_does_not_contain_legacy_marker(self):
        prompt = _load_system_prompt(TargetRuntime.NET8)
        assert "LEGACY MODE" not in prompt

    def test_net48_prompt_appends_legacy_section(self):
        prompt = _load_system_prompt(TargetRuntime.NET48)
        assert "LEGACY MODE" in prompt
        assert ".NET Framework 4.8" in prompt

    def test_prompt_is_nonempty_string(self):
        prompt = _load_system_prompt(TargetRuntime.NET8)
        assert isinstance(prompt, str)
        assert len(prompt) > 0


# ---------------------------------------------------------------------------
# generate_code tests (mocked LLM)
# ---------------------------------------------------------------------------
class TestGenerateCode:
    """Tests for the async generate_code function."""

    @pytest.mark.asyncio
    async def test_returns_generation_result(self, mock_llm_client):
        mock_llm_client.generate.return_value = (
            "Public Sub Main()\n    ' generated\nEnd Sub"
        )
        req = GenerationRequest(
            requirement="Compute IC eliminations",
            rule_type="Finance Business Rule",
            target_runtime=TargetRuntime.NET8,
            project_context={},
        )
        result = await generate_code(mock_llm_client, req)

        assert isinstance(result, GenerationResult)
        assert "Public Sub Main()" in result.source_code
        assert result.target_runtime == TargetRuntime.NET8

    @pytest.mark.asyncio
    async def test_detects_vbnet_language(self, mock_llm_client):
        mock_llm_client.generate.return_value = (
            "Public Sub Main()\n    Dim x As Integer = 1\nEnd Sub"
        )
        req = GenerationRequest(
            requirement="test",
            rule_type="Finance Business Rule",
            target_runtime=TargetRuntime.NET8,
            project_context={},
        )
        result = await generate_code(mock_llm_client, req)
        assert result.language == "vb.net"

    @pytest.mark.asyncio
    async def test_detects_csharp_language(self, mock_llm_client):
        mock_llm_client.generate.return_value = (
            "public void Execute()\n{\n    var x = 1;\n}"
        )
        req = GenerationRequest(
            requirement="test",
            rule_type="Finance Business Rule",
            target_runtime=TargetRuntime.NET8,
            project_context={},
        )
        result = await generate_code(mock_llm_client, req)
        assert result.language == "csharp"

    @pytest.mark.asyncio
    async def test_strips_markdown_code_fences(self, mock_llm_client):
        mock_llm_client.generate.return_value = (
            "```vbnet\nPublic Sub Main()\nEnd Sub\n```"
        )
        req = GenerationRequest(
            requirement="test",
            rule_type="Finance Business Rule",
            target_runtime=TargetRuntime.NET8,
            project_context={},
        )
        result = await generate_code(mock_llm_client, req)
        assert "```" not in result.source_code

    @pytest.mark.asyncio
    async def test_confidence_is_default_085(self, mock_llm_client):
        mock_llm_client.generate.return_value = "Public Sub Main()\nEnd Sub"
        req = GenerationRequest(
            requirement="test",
            rule_type="Finance Business Rule",
            target_runtime=TargetRuntime.NET8,
            project_context={},
        )
        result = await generate_code(mock_llm_client, req)
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_llm_called_with_correct_temperature(self, mock_llm_client):
        mock_llm_client.generate.return_value = "code"
        req = GenerationRequest(
            requirement="test",
            rule_type="Finance Business Rule",
            target_runtime=TargetRuntime.NET8,
            project_context={},
        )
        await generate_code(mock_llm_client, req)

        call_kwargs = mock_llm_client.generate.call_args
        assert call_kwargs.kwargs.get("temperature") == 0.3 or call_kwargs[1].get("temperature") == 0.3

    @pytest.mark.asyncio
    async def test_llm_called_with_none_max_tokens(self, mock_llm_client):
        """generate_code passes max_tokens=None which causes LLMClient to use its default."""
        mock_llm_client.generate.return_value = "code"
        req = GenerationRequest(
            requirement="test",
            rule_type="Finance Business Rule",
            target_runtime=TargetRuntime.NET8,
            project_context={},
        )
        await generate_code(mock_llm_client, req)

        call_kwargs = mock_llm_client.generate.call_args
        # max_tokens should be None (the generator relies on LLMClient default)
        max_tokens_arg = call_kwargs.kwargs.get("max_tokens") if call_kwargs.kwargs else call_kwargs[1].get("max_tokens")
        assert max_tokens_arg is None

    @pytest.mark.asyncio
    async def test_retry_feedback_forwarded_to_llm(self, mock_llm_client):
        mock_llm_client.generate.return_value = "code"
        req = GenerationRequest(
            requirement="test",
            rule_type="Finance Business Rule",
            target_runtime=TargetRuntime.NET8,
            project_context={},
            retry_feedback="Add error handling",
        )
        await generate_code(mock_llm_client, req)

        user_msg = mock_llm_client.generate.call_args.kwargs.get("user_message", "")
        if not user_msg:
            user_msg = mock_llm_client.generate.call_args[1].get("user_message", "")
        assert "Add error handling" in user_msg
