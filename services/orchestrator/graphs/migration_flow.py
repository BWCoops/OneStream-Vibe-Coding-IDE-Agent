"""
Migration workflow — LangGraph workflow.

Translates SAP BPC Script Logic or Oracle HFM rules into OneStream VB.NET.

Flow:
1. requirements — Discover requirements from the source code and context
2. translate — Use migration agent to translate source → OneStream VB.NET
3. review — Code reviewer validates translated code (2x context budget)
4. test — Test engineer generates test cases for translated code
5. finalize — Produce final migration result with review and tests
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

import structlog
from langgraph.graph import END, StateGraph

from agents.code_reviewer import ReviewRequest, review_code
from agents.migration import translate_code
from agents.requirements import discover_requirements
from agents.test_engineer import TestGenerationRequest, generate_tests
from llm_client import LLMClient

logger = structlog.get_logger()

MAX_RETRIES = 2


def _merge_list(a: list, b: list) -> list:
    return a + b


class MigrationFlowState(TypedDict, total=False):
    """State passed through the LangGraph migration workflow."""

    # Input
    source_code: str
    source_platform: str  # "bpc" or "hfm"
    target_runtime: str  # "net8.0" or "net48"
    project_context: dict[str, Any]

    # Requirements phase
    requirements: Annotated[list[dict], _merge_list]
    assumptions: Annotated[list[str], _merge_list]
    questions: Annotated[list[str], _merge_list]

    # Translation phase
    translated_code: str
    translation_notes: Annotated[list[str], _merge_list]
    translation_warnings: Annotated[list[str], _merge_list]

    # Review phase
    review_passed: bool
    review_score: float
    review_feedback: str
    review_findings: list[dict]
    retry_count: int

    # Test phase
    test_cases: Annotated[list[dict], _merge_list]

    # Output
    final_code: str
    final_status: str

    # Internal
    _llm: LLMClient


# ---------------------------------------------------------------------------
# Node 1 — Requirements Discovery
# ---------------------------------------------------------------------------

async def requirements_node(state: MigrationFlowState) -> dict:
    """Discover requirements from the migration context."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    source_platform = state.get("source_platform", "unknown")
    user_input = (
        f"Migrate {source_platform.upper()} code to OneStream VB.NET.\n\n"
        f"Source code ({source_platform}):\n```\n{state.get('source_code', '')[:2000]}\n```\n\n"
        f"Target runtime: {state.get('target_runtime', 'net8.0')}"
    )

    logger.info("migration_flow.requirements", source_platform=source_platform)

    result = await discover_requirements(
        llm=llm,
        user_input=user_input,
        project_context=state.get("project_context", {}),
    )

    return {
        "requirements": [
            {
                "id": r.id,
                "category": r.category,
                "title": r.title,
                "description": r.description,
                "acceptance_criteria": r.acceptance_criteria,
                "priority": r.priority,
            }
            for r in result.requirements
        ],
        "assumptions": result.assumptions,
        "questions": result.questions,
    }


# ---------------------------------------------------------------------------
# Node 2 — Translation
# ---------------------------------------------------------------------------

async def translate_node(state: MigrationFlowState) -> dict:
    """Translate source code using the migration agent."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("migration_flow.translate", source_platform=state.get("source_platform", ""))

    result = await translate_code(
        llm=llm,
        source_code=state.get("source_code", ""),
        source_platform=state.get("source_platform", "bpc"),
        target_runtime=state.get("target_runtime", "net8.0"),
    )

    return {
        "translated_code": result.translated_code,
        "translation_notes": result.translation_notes,
        "translation_warnings": result.warnings,
    }


# ---------------------------------------------------------------------------
# Node 3 — Code Review
# ---------------------------------------------------------------------------

async def review_node(state: MigrationFlowState) -> dict:
    """Review the translated code with the critic agent (2x context)."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("migration_flow.review")

    source_platform = state.get("source_platform", "unknown")
    requirement = (
        f"Migration from {source_platform.upper()} to OneStream VB.NET. "
        f"Original {source_platform} code was {len(state.get('source_code', ''))} characters."
    )

    request = ReviewRequest(
        source_code=state.get("translated_code", ""),
        language="vb.net",
        target_runtime=state.get("target_runtime", "net8.0"),
        rule_type="Finance",
        original_requirement=requirement,
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


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def should_retry(state: MigrationFlowState) -> Literal["retry", "test"]:
    """Route after review: retry translation or proceed to tests."""
    if state.get("review_passed", False):
        return "test"

    retry_count = state.get("retry_count", 0)
    if retry_count < MAX_RETRIES:
        return "retry"

    # Max retries exhausted — proceed to tests anyway
    logger.warning("migration_flow.max_retries", score=state.get("review_score", 0.0))
    return "test"


async def increment_retry(state: MigrationFlowState) -> dict:
    """Increment retry counter before re-translation."""
    return {"retry_count": state.get("retry_count", 0) + 1}


# ---------------------------------------------------------------------------
# Node 4 — Test Generation
# ---------------------------------------------------------------------------

async def test_node(state: MigrationFlowState) -> dict:
    """Generate test cases for the translated code."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("migration_flow.test_generation")

    source_platform = state.get("source_platform", "unknown")
    requirement = (
        f"Migrated from {source_platform.upper()} to OneStream VB.NET. "
        f"Verify that the translated code preserves the original business logic."
    )

    request = TestGenerationRequest(
        source_code=state.get("translated_code", ""),
        rule_type="Finance",
        requirement=requirement,
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


# ---------------------------------------------------------------------------
# Node 5 — Finalize
# ---------------------------------------------------------------------------

async def finalize_node(state: MigrationFlowState) -> dict:
    """Produce the final migration result."""
    passed = state.get("review_passed", False)
    return {
        "final_code": state.get("translated_code", ""),
        "final_status": "approved" if passed else "review_failed",
    }


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_migration_flow_graph() -> StateGraph:
    """Build and compile the migration workflow graph."""
    graph = StateGraph(MigrationFlowState)

    # Add nodes
    graph.add_node("requirements", requirements_node)
    graph.add_node("translate", translate_node)
    graph.add_node("review", review_node)
    graph.add_node("increment_retry", increment_retry)
    graph.add_node("test", test_node)
    graph.add_node("finalize", finalize_node)

    # Edges: requirements → translate → review → [retry/test] → finalize
    graph.add_edge("requirements", "translate")
    graph.add_edge("translate", "review")
    graph.add_conditional_edges(
        "review",
        should_retry,
        {
            "retry": "increment_retry",
            "test": "test",
        },
    )
    graph.add_edge("increment_retry", "translate")
    graph.add_edge("test", "finalize")
    graph.add_edge("finalize", END)

    # Entry point
    graph.set_entry_point("requirements")

    return graph


# Compile the graph
migration_flow_graph = build_migration_flow_graph()
