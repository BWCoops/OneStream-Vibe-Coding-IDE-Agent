"""
Generator → Critic → Test loop — LangGraph workflow.

This is the default code generation flow:
1. Code Generator produces VB.NET/C#
2. Code Reviewer (critic, 2x context) validates
3. If review fails → feedback loop to generator (max 3 retries)
4. If review passes → Test Engineer generates tests
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

import structlog
from langgraph.graph import END, StateGraph

from agents.code_generator import GenerationRequest, TargetRuntime, generate_code
from agents.code_reviewer import ReviewRequest, review_code
from agents.test_engineer import TestGenerationRequest, generate_tests
from llm_client import LLMClient

logger = structlog.get_logger()

MAX_RETRIES = 3


def _merge_list(a: list, b: list) -> list:
    return a + b


class CodeGenState(TypedDict, total=False):
    """State passed through the LangGraph code generation workflow."""

    # Input
    requirement: str
    rule_type: str
    target_runtime: str
    project_context: dict[str, Any]

    # Intermediate
    generated_code: str
    review_passed: bool
    review_score: float
    review_feedback: str
    review_findings: list[dict]
    retry_count: int

    # Output
    test_cases: Annotated[list[dict], _merge_list]
    final_code: str
    final_status: str


async def generate_node(state: CodeGenState) -> dict:
    """Code Generator node — produces VB.NET/C# from requirement."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]
    retry_count = state.get("retry_count", 0)

    logger.info("graph.generate", retry=retry_count)

    request = GenerationRequest(
        requirement=state["requirement"],
        rule_type=state["rule_type"],
        target_runtime=TargetRuntime(state["target_runtime"]),
        project_context=state.get("project_context", {}),
        retry_feedback=state.get("review_feedback", ""),
    )

    result = await generate_code(llm, request)
    return {"generated_code": result.source_code}


async def review_node(state: CodeGenState) -> dict:
    """Code Reviewer node — validates with 2x context budget."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("graph.review", code_length=len(state.get("generated_code", "")))

    request = ReviewRequest(
        source_code=state.get("generated_code", ""),
        language="vb.net",
        target_runtime=state["target_runtime"],
        rule_type=state["rule_type"],
        original_requirement=state["requirement"],
    )

    result = await review_code(llm, request)

    return {
        "review_passed": result.passed,
        "review_score": result.score,
        "review_feedback": result.retry_guidance,
        "review_findings": [
            {
                "category": f.category.value,
                "severity": f.severity.value,
                "message": f.message,
                "line": f.line,
                "suggestion": f.suggestion,
            }
            for f in result.findings
        ],
    }


def should_retry(state: CodeGenState) -> Literal["generate", "test", "finalize"]:
    """Route after review: retry generation, proceed to tests, or finalize."""
    if state.get("review_passed", False):
        return "test"

    retry_count = state.get("retry_count", 0)
    if retry_count < MAX_RETRIES:
        return "generate"

    logger.warning("graph.max_retries_reached", score=state.get("review_score", 0.0))
    return "finalize"


async def increment_retry(state: CodeGenState) -> dict:
    """Increment retry counter before re-generation."""
    return {"retry_count": state.get("retry_count", 0) + 1}


async def test_node(state: CodeGenState) -> dict:
    """Test Engineer node — generates tests for approved code."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("graph.test_generation")

    request = TestGenerationRequest(
        source_code=state.get("generated_code", ""),
        rule_type=state["rule_type"],
        requirement=state["requirement"],
    )

    tests = await generate_tests(llm, request)
    return {
        "test_cases": [
            {
                "id": t.id,
                "type": t.type.value,
                "name": t.name,
                "description": t.description,
                "test_script": t.test_script,
                "expected_result": t.expected_result,
            }
            for t in tests
        ],
    }


async def finalize_node(state: CodeGenState) -> dict:
    """Set final output status."""
    passed = state.get("review_passed", False)
    return {
        "final_code": state.get("generated_code", ""),
        "final_status": "approved" if passed else "review_failed",
    }


def build_code_gen_graph() -> StateGraph:
    """Build and compile the code generation workflow graph."""
    graph = StateGraph(CodeGenState)

    # Add nodes
    graph.add_node("generate", generate_node)
    graph.add_node("review", review_node)
    graph.add_node("increment_retry", increment_retry)
    graph.add_node("test", test_node)
    graph.add_node("finalize", finalize_node)

    # Edges
    graph.add_edge("generate", "review")
    graph.add_conditional_edges(
        "review",
        should_retry,
        {
            "generate": "increment_retry",
            "test": "test",
            "finalize": "finalize",
        },
    )
    graph.add_edge("increment_retry", "generate")
    graph.add_edge("test", "finalize")
    graph.add_edge("finalize", END)

    # Entry point
    graph.set_entry_point("generate")

    return graph


# Compile the graph
code_gen_graph = build_code_gen_graph()
