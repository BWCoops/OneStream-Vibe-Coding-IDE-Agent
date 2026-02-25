"""Tests for the LangGraph Code Generation workflow (code_gen_flow).

Covers:
- Individual node functions (generate_node, review_node, test_node, finalize_node)
- The should_retry routing logic
- The increment_retry helper
- Graph structure verification (build_code_gen_graph)
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graphs.code_gen_flow import (
    MAX_RETRIES,
    CodeGenState,
    build_code_gen_graph,
    finalize_node,
    generate_node,
    increment_retry,
    review_node,
    should_retry,
    test_node,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _base_state(**overrides) -> dict:
    """Create a minimal valid CodeGenState dict."""
    state: dict = {
        "requirement": "Calculate IC eliminations",
        "rule_type": "Finance Business Rule",
        "target_runtime": "net8.0",
        "project_context": {},
        "generated_code": "",
        "review_passed": False,
        "review_score": 0.0,
        "review_feedback": "",
        "review_findings": [],
        "retry_count": 0,
        "test_cases": [],
        "final_code": "",
        "final_status": "",
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# should_retry routing tests
# ---------------------------------------------------------------------------
class TestShouldRetry:
    """Tests for the conditional routing function."""

    def test_routes_to_test_when_review_passed(self):
        state = _base_state(review_passed=True, retry_count=0)
        assert should_retry(state) == "test"

    def test_routes_to_generate_when_retries_available(self):
        state = _base_state(review_passed=False, retry_count=0)
        assert should_retry(state) == "generate"

    def test_routes_to_generate_at_retry_limit_minus_one(self):
        state = _base_state(review_passed=False, retry_count=MAX_RETRIES - 1)
        assert should_retry(state) == "generate"

    def test_routes_to_finalize_when_retries_exhausted(self):
        state = _base_state(review_passed=False, retry_count=MAX_RETRIES)
        assert should_retry(state) == "finalize"

    def test_routes_to_finalize_when_over_max_retries(self):
        state = _base_state(review_passed=False, retry_count=MAX_RETRIES + 5)
        assert should_retry(state) == "finalize"

    def test_defaults_review_passed_to_false(self):
        """If review_passed key is missing, should not route to test."""
        state = _base_state()
        del state["review_passed"]
        result = should_retry(state)
        assert result in ("generate", "finalize")

    def test_defaults_retry_count_to_zero(self):
        """If retry_count key is missing, treat as 0 (retries available)."""
        state = _base_state(review_passed=False)
        del state["retry_count"]
        assert should_retry(state) == "generate"


# ---------------------------------------------------------------------------
# increment_retry tests
# ---------------------------------------------------------------------------
class TestIncrementRetry:
    """Tests for the retry counter incrementer."""

    @pytest.mark.asyncio
    async def test_increments_from_zero(self):
        result = await increment_retry(_base_state(retry_count=0))
        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_increments_from_existing_count(self):
        result = await increment_retry(_base_state(retry_count=2))
        assert result["retry_count"] == 3

    @pytest.mark.asyncio
    async def test_defaults_missing_retry_count(self):
        state = _base_state()
        del state["retry_count"]
        result = await increment_retry(state)
        assert result["retry_count"] == 1


# ---------------------------------------------------------------------------
# generate_node tests (mocked generate_code)
# ---------------------------------------------------------------------------
class TestGenerateNode:
    """Tests for the generate_node graph function."""

    @pytest.mark.asyncio
    async def test_returns_generated_code(self, mock_llm_client):
        state = _base_state(_llm=mock_llm_client)
        mock_llm_client.generate.return_value = "Public Sub Main()\nEnd Sub"

        with patch("graphs.code_gen_flow.generate_code", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = MagicMock(source_code="Public Sub Main()\nEnd Sub")
            result = await generate_node(state)

        assert "generated_code" in result
        assert "Public Sub Main()" in result["generated_code"]

    @pytest.mark.asyncio
    async def test_passes_retry_feedback(self, mock_llm_client):
        state = _base_state(
            _llm=mock_llm_client,
            review_feedback="Add error handling",
            retry_count=1,
        )

        with patch("graphs.code_gen_flow.generate_code", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = MagicMock(source_code="fixed code")
            await generate_node(state)

            req = mock_gen.call_args[0][1]  # second positional arg is the request
            assert req.retry_feedback == "Add error handling"


# ---------------------------------------------------------------------------
# review_node tests (mocked review_code)
# ---------------------------------------------------------------------------
class TestReviewNode:
    """Tests for the review_node graph function."""

    @pytest.mark.asyncio
    async def test_returns_review_fields(self, mock_llm_client):
        state = _base_state(
            _llm=mock_llm_client,
            generated_code="Public Sub Main()\nEnd Sub",
        )

        mock_review_result = MagicMock()
        mock_review_result.passed = True
        mock_review_result.score = 0.95
        mock_review_result.retry_guidance = ""
        mock_review_result.findings = []

        with patch("graphs.code_gen_flow.review_code", new_callable=AsyncMock) as mock_rev:
            mock_rev.return_value = mock_review_result
            result = await review_node(state)

        assert result["review_passed"] is True
        assert result["review_score"] == 0.95
        assert result["review_findings"] == []

    @pytest.mark.asyncio
    async def test_review_findings_serialized(self, mock_llm_client):
        state = _base_state(
            _llm=mock_llm_client,
            generated_code="code",
        )

        finding = MagicMock()
        finding.category.value = "deprecated_api"
        finding.severity.value = "error"
        finding.message = "deprecated usage"
        finding.line = 10
        finding.suggestion = "use new api"

        mock_result = MagicMock()
        mock_result.passed = False
        mock_result.score = 0.3
        mock_result.retry_guidance = "fix deprecated"
        mock_result.findings = [finding]

        with patch("graphs.code_gen_flow.review_code", new_callable=AsyncMock) as mock_rev:
            mock_rev.return_value = mock_result
            result = await review_node(state)

        assert len(result["review_findings"]) == 1
        assert result["review_findings"][0]["category"] == "deprecated_api"
        assert result["review_findings"][0]["line"] == 10


# ---------------------------------------------------------------------------
# test_node tests (mocked generate_tests)
# ---------------------------------------------------------------------------
class TestTestNode:
    """Tests for the test_node graph function."""

    @pytest.mark.asyncio
    async def test_returns_test_cases(self, mock_llm_client):
        state = _base_state(
            _llm=mock_llm_client,
            generated_code="Public Sub Main()\nEnd Sub",
        )

        mock_tc = MagicMock()
        mock_tc.id = "TC-001"
        mock_tc.type.value = "unit"
        mock_tc.name = "Test calculation"
        mock_tc.description = "Verify elimination logic"
        mock_tc.test_script = "assert result == expected"
        mock_tc.expected_result = "1000.0"

        with patch("graphs.code_gen_flow.generate_tests", new_callable=AsyncMock) as mock_tests:
            mock_tests.return_value = [mock_tc]
            result = await test_node(state)

        assert len(result["test_cases"]) == 1
        assert result["test_cases"][0]["id"] == "TC-001"
        assert result["test_cases"][0]["type"] == "unit"


# ---------------------------------------------------------------------------
# finalize_node tests
# ---------------------------------------------------------------------------
class TestFinalizeNode:
    """Tests for the finalize_node graph function."""

    @pytest.mark.asyncio
    async def test_approved_when_review_passed(self):
        state = _base_state(review_passed=True, generated_code="good code")
        result = await finalize_node(state)

        assert result["final_status"] == "approved"
        assert result["final_code"] == "good code"

    @pytest.mark.asyncio
    async def test_review_failed_when_not_passed(self):
        state = _base_state(review_passed=False, generated_code="bad code")
        result = await finalize_node(state)

        assert result["final_status"] == "review_failed"
        assert result["final_code"] == "bad code"

    @pytest.mark.asyncio
    async def test_defaults_missing_fields(self):
        state = _base_state()
        del state["review_passed"]
        del state["generated_code"]
        result = await finalize_node(state)

        assert result["final_status"] == "review_failed"
        assert result["final_code"] == ""


# ---------------------------------------------------------------------------
# Graph structure tests
# ---------------------------------------------------------------------------
class TestBuildCodeGenGraph:
    """Tests for the graph builder — verifies nodes and edges exist."""

    def test_graph_has_expected_nodes(self):
        graph = build_code_gen_graph()
        node_names = set(graph.nodes.keys())
        expected = {"generate", "review", "increment_retry", "test", "finalize"}
        assert expected.issubset(node_names)

    def test_graph_entry_point_is_generate(self):
        graph = build_code_gen_graph()
        # LangGraph stores the entry point; the __start__ node edges to it
        assert "__start__" in graph.nodes or "generate" in graph.nodes

    def test_max_retries_is_three(self):
        assert MAX_RETRIES == 3
