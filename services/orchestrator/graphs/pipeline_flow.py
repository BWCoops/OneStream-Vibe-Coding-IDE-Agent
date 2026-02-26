"""
Data pipeline generation flow — LangGraph workflow.

Flow:
1. requirements — Discover requirements from the pipeline request
2. pipeline_design — Generate pipeline DAG, connectors, and validation rules
3. adapter_codegen — Generate OneStream Data Adapter business rule code
4. adapter_review — Review the generated adapter code (critic, 2x context)
5. finalize — Produce final pipeline definition with approved adapter code
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

import structlog
from langgraph.graph import END, StateGraph

from agents.code_generator import GenerationRequest, TargetRuntime, generate_code
from agents.code_reviewer import ReviewRequest, review_code
from agents.data_orchestration import design_pipeline
from agents.requirements import discover_requirements
from llm_client import LLMClient

logger = structlog.get_logger()

MAX_RETRIES = 2


def _merge_list(a: list, b: list) -> list:
    return a + b


class PipelineFlowState(TypedDict, total=False):
    """State passed through the LangGraph pipeline generation workflow."""

    # Input
    user_request: str
    project_context: dict[str, Any]
    target_runtime: str

    # Requirements phase
    requirements: Annotated[list[dict], _merge_list]
    assumptions: Annotated[list[str], _merge_list]
    questions: Annotated[list[str], _merge_list]

    # Pipeline design phase
    pipeline_name: str
    pipeline_description: str
    stages: list[dict]
    schedule: dict | None
    sla_target_minutes: int | None

    # Adapter code generation phase
    adapter_code: str
    review_passed: bool
    review_score: float
    review_feedback: str
    review_findings: list[dict]
    retry_count: int

    # Output
    final_pipeline: dict
    final_status: str

    # Internal
    _llm: LLMClient


# ---------------------------------------------------------------------------
# Node 1 — Requirements Discovery
# ---------------------------------------------------------------------------

async def requirements_node(state: PipelineFlowState) -> dict:
    """Discover requirements from the pipeline request."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("pipeline_flow.requirements", request_length=len(state.get("user_request", "")))

    result = await discover_requirements(
        llm=llm,
        user_input=state["user_request"],
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
# Node 2 — Pipeline Design
# ---------------------------------------------------------------------------

async def design_node(state: PipelineFlowState) -> dict:
    """Generate the pipeline DAG, connectors, and stage definitions."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("pipeline_flow.design")

    # Enrich request with discovered requirements
    requirements = state.get("requirements", [])
    enriched_context = {
        **state.get("project_context", {}),
        "requirements": str(requirements),
    }

    result = await design_pipeline(
        llm=llm,
        user_request=state["user_request"],
        project_context=enriched_context,
    )

    return {
        "pipeline_name": result.name,
        "pipeline_description": result.description,
        "stages": result.stages,
        "schedule": result.schedule,
        "sla_target_minutes": result.sla_target_minutes,
        "adapter_code": result.generated_adapter_code,
    }


# ---------------------------------------------------------------------------
# Node 3 — Adapter Code Generation (if not produced by design agent)
# ---------------------------------------------------------------------------

async def adapter_codegen_node(state: PipelineFlowState) -> dict:
    """Generate OneStream Data Adapter code if not already produced."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]
    existing_code = state.get("adapter_code", "")

    if existing_code and len(existing_code) > 50:
        logger.info("pipeline_flow.adapter_codegen.skipped", reason="already_generated")
        return {}

    logger.info("pipeline_flow.adapter_codegen")

    # Build requirement from pipeline design
    stages_desc = "\n".join(
        f"- Stage {s.get('id', '?')}: {s.get('type', '?')} — {s.get('name', '?')}"
        for s in state.get("stages", [])
    )
    requirement = (
        f"Generate a OneStream Data Adapter business rule for pipeline '{state.get('pipeline_name', '')}'.\n"
        f"Pipeline description: {state.get('pipeline_description', '')}\n"
        f"Stages:\n{stages_desc}\n"
        f"The adapter must handle data extraction, transformation, validation, and loading."
    )

    runtime = state.get("target_runtime", "net8.0")
    request = GenerationRequest(
        requirement=requirement,
        rule_type="DataManagementExtender",
        target_runtime=TargetRuntime(runtime),
        project_context=state.get("project_context", {}),
        retry_feedback=state.get("review_feedback", ""),
    )

    result = await generate_code(llm, request)
    return {"adapter_code": result.source_code}


# ---------------------------------------------------------------------------
# Node 4 — Adapter Code Review
# ---------------------------------------------------------------------------

async def adapter_review_node(state: PipelineFlowState) -> dict:
    """Review the generated adapter code with 2x context budget."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("pipeline_flow.adapter_review")

    request = ReviewRequest(
        source_code=state.get("adapter_code", ""),
        language="vb.net",
        target_runtime=state.get("target_runtime", "net8.0"),
        rule_type="DataManagementExtender",
        original_requirement=state.get("user_request", ""),
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

def should_retry_adapter(state: PipelineFlowState) -> Literal["retry", "finalize"]:
    """Route after adapter review: retry or finalize."""
    if state.get("review_passed", False):
        return "finalize"

    retry_count = state.get("retry_count", 0)
    if retry_count < MAX_RETRIES:
        return "retry"

    logger.warning("pipeline_flow.max_retries", score=state.get("review_score", 0.0))
    return "finalize"


async def increment_retry(state: PipelineFlowState) -> dict:
    """Increment retry counter before adapter re-generation."""
    return {"retry_count": state.get("retry_count", 0) + 1}


# ---------------------------------------------------------------------------
# Node 5 — Finalize
# ---------------------------------------------------------------------------

async def finalize_node(state: PipelineFlowState) -> dict:
    """Assemble the final pipeline definition."""
    passed = state.get("review_passed", False)

    final_pipeline = {
        "name": state.get("pipeline_name", ""),
        "description": state.get("pipeline_description", ""),
        "stages": state.get("stages", []),
        "schedule": state.get("schedule"),
        "sla_target_minutes": state.get("sla_target_minutes"),
        "adapter_code": state.get("adapter_code", ""),
        "review_score": state.get("review_score", 0.0),
        "review_findings": state.get("review_findings", []),
        "requirements": state.get("requirements", []),
        "assumptions": state.get("assumptions", []),
        "questions": state.get("questions", []),
    }

    return {
        "final_pipeline": final_pipeline,
        "final_status": "approved" if passed else "review_failed",
    }


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_pipeline_flow_graph() -> StateGraph:
    """Build and compile the data pipeline generation workflow graph."""
    graph = StateGraph(PipelineFlowState)

    # Add nodes
    graph.add_node("requirements", requirements_node)
    graph.add_node("design", design_node)
    graph.add_node("adapter_codegen", adapter_codegen_node)
    graph.add_node("adapter_review", adapter_review_node)
    graph.add_node("increment_retry", increment_retry)
    graph.add_node("finalize", finalize_node)

    # Edges: requirements → design → adapter_codegen → adapter_review → [retry/finalize]
    graph.add_edge("requirements", "design")
    graph.add_edge("design", "adapter_codegen")
    graph.add_edge("adapter_codegen", "adapter_review")
    graph.add_conditional_edges(
        "adapter_review",
        should_retry_adapter,
        {
            "retry": "increment_retry",
            "finalize": "finalize",
        },
    )
    graph.add_edge("increment_retry", "adapter_codegen")
    graph.add_edge("finalize", END)

    # Entry point
    graph.set_entry_point("requirements")

    return graph


# Compile the graph
pipeline_flow_graph = build_pipeline_flow_graph()
