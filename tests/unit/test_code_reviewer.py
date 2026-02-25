"""Tests for the Code Reviewer (Verification) Agent.

Covers:
- JSON response parsing (valid JSON, markdown-wrapped JSON, malformed JSON)
- Review finding construction
- Severity / category enum handling
- Fallback on parse failure
- The review_code async function with mocked LLM
"""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from agents.code_reviewer import (
    ReviewCategory,
    ReviewFinding,
    ReviewRequest,
    ReviewResult,
    ReviewSeverity,
    _build_review_message,
    _parse_review_response,
    review_code,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_review_json(
    passed: bool = True,
    score: float = 0.92,
    findings: list[dict] | None = None,
    summary: str = "Looks good",
    retry_guidance: str = "",
) -> str:
    """Build a valid review JSON response string."""
    if findings is None:
        findings = []
    return json.dumps(
        {
            "passed": passed,
            "score": score,
            "findings": findings,
            "summary": summary,
            "retry_guidance": retry_guidance,
        }
    )


# ---------------------------------------------------------------------------
# _parse_review_response tests
# ---------------------------------------------------------------------------
class TestParseReviewResponse:
    """Tests for parsing the LLM's JSON review response."""

    def test_parses_clean_json(self):
        raw = _make_review_json(passed=True, score=0.95, summary="All checks pass")
        result = _parse_review_response(raw)

        assert isinstance(result, ReviewResult)
        assert result.passed is True
        assert result.score == 0.95
        assert result.summary == "All checks pass"

    def test_parses_json_in_markdown_code_block(self):
        raw = "```json\n" + _make_review_json(passed=False, score=0.4) + "\n```"
        result = _parse_review_response(raw)

        assert result.passed is False
        assert result.score == 0.4

    def test_parses_json_in_plain_code_block(self):
        raw = "```\n" + _make_review_json(score=0.7) + "\n```"
        result = _parse_review_response(raw)

        assert result.score == 0.7

    def test_parses_findings_with_all_fields(self):
        findings = [
            {
                "category": "deprecated_api",
                "severity": "error",
                "message": "BRApi.Utilities.EncryptText is deprecated",
                "line": 42,
                "suggestion": "Use DPAPI or platform encryption",
            }
        ]
        raw = _make_review_json(passed=False, score=0.3, findings=findings)
        result = _parse_review_response(raw)

        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.category == ReviewCategory.DEPRECATED_API
        assert f.severity == ReviewSeverity.ERROR
        assert "EncryptText" in f.message
        assert f.line == 42
        assert "DPAPI" in f.suggestion

    def test_parses_multiple_findings(self):
        findings = [
            {"category": "security", "severity": "warning", "message": "Hardcoded credential"},
            {"category": "performance", "severity": "info", "message": "Consider bulk operations"},
            {"category": "error_handling", "severity": "error", "message": "Missing Try/Catch"},
        ]
        raw = _make_review_json(findings=findings)
        result = _parse_review_response(raw)

        assert len(result.findings) == 3
        categories = {f.category for f in result.findings}
        assert ReviewCategory.SECURITY in categories
        assert ReviewCategory.PERFORMANCE in categories
        assert ReviewCategory.ERROR_HANDLING in categories

    def test_defaults_for_missing_finding_fields(self):
        findings = [{"message": "Something is off"}]
        raw = _make_review_json(findings=findings)
        result = _parse_review_response(raw)

        f = result.findings[0]
        assert f.category == ReviewCategory.CORRECTNESS  # default
        assert f.severity == ReviewSeverity.INFO  # default
        assert f.line is None
        assert f.suggestion == ""

    def test_retry_guidance_extracted(self):
        raw = _make_review_json(
            passed=False,
            retry_guidance="Add structured error handling with BRApi.ErrorLog",
        )
        result = _parse_review_response(raw)

        assert "BRApi.ErrorLog" in result.retry_guidance

    def test_malformed_json_returns_failed_result(self):
        raw = "This is not JSON at all {{{ bad"
        result = _parse_review_response(raw)

        assert result.passed is False
        assert result.score == 0.0
        assert len(result.findings) == 1
        assert result.findings[0].severity == ReviewSeverity.ERROR
        assert "parse" in result.findings[0].message.lower()

    def test_empty_string_returns_failed_result(self):
        result = _parse_review_response("")
        assert result.passed is False

    def test_partial_json_missing_passed_defaults_false(self):
        raw = json.dumps({"score": 0.8, "findings": [], "summary": "ok"})
        result = _parse_review_response(raw)
        assert result.passed is False  # default when 'passed' key missing

    def test_invalid_category_raises_graceful_fallback(self):
        """An unknown category value should cause a parse error and fallback."""
        raw = json.dumps(
            {
                "passed": True,
                "score": 0.9,
                "findings": [
                    {"category": "nonexistent_category", "severity": "error", "message": "test"}
                ],
                "summary": "ok",
            }
        )
        result = _parse_review_response(raw)
        # ValueError from ReviewCategory("nonexistent_category") triggers the except branch
        assert result.passed is False
        assert result.score == 0.0


# ---------------------------------------------------------------------------
# _build_review_message tests
# ---------------------------------------------------------------------------
class TestBuildReviewMessage:
    """Tests for the review prompt construction."""

    def _make_request(self, **overrides) -> ReviewRequest:
        defaults = dict(
            source_code="Public Sub Main()\nEnd Sub",
            language="vb.net",
            target_runtime="net8.0",
            rule_type="Finance Business Rule",
            original_requirement="Calculate IC eliminations",
            requirement_id=None,
            test_cases=[],
        )
        defaults.update(overrides)
        return ReviewRequest(**defaults)

    def test_includes_source_code(self):
        req = self._make_request()
        msg = _build_review_message(req)
        assert "Public Sub Main()" in msg
        assert "## Source Code to Review" in msg

    def test_includes_original_requirement(self):
        req = self._make_request()
        msg = _build_review_message(req)
        assert "Calculate IC eliminations" in msg

    def test_includes_requirement_id_when_present(self):
        req = self._make_request(requirement_id="REQ-042")
        msg = _build_review_message(req)
        assert "REQ-042" in msg

    def test_omits_requirement_id_when_none(self):
        req = self._make_request(requirement_id=None)
        msg = _build_review_message(req)
        assert "## Requirement ID" not in msg

    def test_includes_test_cases(self):
        req = self._make_request(test_cases=["test A", "test B"])
        msg = _build_review_message(req)
        assert "test A" in msg
        assert "test B" in msg

    def test_test_cases_truncated_to_five(self):
        cases = [f"test_{i}" for i in range(10)]
        req = self._make_request(test_cases=cases)
        msg = _build_review_message(req)
        assert "test_4" in msg
        assert "test_5" not in msg

    def test_includes_deprecated_api_section(self):
        req = self._make_request()
        msg = _build_review_message(req)
        assert "## Deprecated API Registry" in msg


# ---------------------------------------------------------------------------
# review_code tests (mocked LLM)
# ---------------------------------------------------------------------------
class TestReviewCode:
    """Tests for the async review_code function."""

    @pytest.mark.asyncio
    async def test_returns_review_result_on_valid_response(self, mock_llm_client):
        mock_llm_client.generate.return_value = _make_review_json(
            passed=True, score=0.95, summary="Code is correct"
        )
        req = ReviewRequest(
            source_code="Public Sub Main()\nEnd Sub",
            language="vb.net",
            target_runtime="net8.0",
            rule_type="Finance Business Rule",
            original_requirement="test requirement",
        )
        result = await review_code(mock_llm_client, req)

        assert isinstance(result, ReviewResult)
        assert result.passed is True
        assert result.score == 0.95

    @pytest.mark.asyncio
    async def test_uses_reviewer_max_tokens(self, mock_llm_client):
        mock_llm_client.generate.return_value = _make_review_json()
        req = ReviewRequest(
            source_code="code",
            language="vb.net",
            target_runtime="net8.0",
            rule_type="Finance Business Rule",
            original_requirement="test",
        )
        await review_code(mock_llm_client, req)

        call_kwargs = mock_llm_client.generate.call_args
        max_tokens = call_kwargs.kwargs.get("max_tokens") or call_kwargs[1].get("max_tokens")
        assert max_tokens == mock_llm_client.config.reviewer_max_tokens

    @pytest.mark.asyncio
    async def test_uses_lower_temperature(self, mock_llm_client):
        mock_llm_client.generate.return_value = _make_review_json()
        req = ReviewRequest(
            source_code="code",
            language="vb.net",
            target_runtime="net8.0",
            rule_type="Finance Business Rule",
            original_requirement="test",
        )
        await review_code(mock_llm_client, req)

        call_kwargs = mock_llm_client.generate.call_args
        temperature = call_kwargs.kwargs.get("temperature") or call_kwargs[1].get("temperature")
        assert temperature == 0.2

    @pytest.mark.asyncio
    async def test_handles_llm_returning_garbage(self, mock_llm_client):
        mock_llm_client.generate.return_value = "I cannot review this code."
        req = ReviewRequest(
            source_code="code",
            language="vb.net",
            target_runtime="net8.0",
            rule_type="Finance Business Rule",
            original_requirement="test",
        )
        result = await review_code(mock_llm_client, req)

        assert result.passed is False
        assert result.score == 0.0
        assert len(result.findings) >= 1
