"""
6-phase requirements discovery workflow — LangGraph workflow.

Phases:
1. gather_context — Use planning agent to understand the request
2. extract_requirements — Use requirements agent to identify discrete requirements
3. generate_acceptance — For each requirement, generate testable acceptance criteria
4. identify_assumptions — Flag assumptions needing validation
5. gap_analysis — Check for missing information, generate clarifying questions
6. generate_frd — Produce FRD/TDD section text
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

import structlog
from langgraph.graph import END, StateGraph

from agents.planning import create_plan
from agents.requirements import discover_requirements
from llm_client import LLMClient

logger = structlog.get_logger()


def _merge_list(a: list, b: list) -> list:
    return a + b


class DiscoveryState(TypedDict, total=False):
    """State passed through the LangGraph discovery workflow."""

    # Input
    user_input: str
    project_context: dict[str, Any]

    # Intermediate / Output
    requirements: Annotated[list[dict], _merge_list]
    assumptions: Annotated[list[str], _merge_list]
    questions: Annotated[list[str], _merge_list]
    frd_section: str
    phase: str

    # Internal
    _llm: LLMClient


# ---------------------------------------------------------------------------
# Phase 1 — Gather Context
# ---------------------------------------------------------------------------

async def gather_context(state: DiscoveryState) -> dict:
    """Use planning agent to understand the request and build initial context."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("discovery.gather_context", input_length=len(state.get("user_input", "")))

    plan = await create_plan(
        llm=llm,
        user_request=state["user_input"],
        project_context=state.get("project_context", {}),
    )

    # Enrich project context with the execution plan for downstream phases
    enriched_context = {
        **state.get("project_context", {}),
        "execution_plan": {
            "tasks": [
                {
                    "id": t.id,
                    "type": t.type.value,
                    "description": t.description,
                    "dependencies": t.dependencies,
                    "priority": t.priority,
                }
                for t in plan.tasks
            ],
            "execution_order": plan.execution_order,
        },
    }

    return {
        "project_context": enriched_context,
        "phase": "gather_context",
    }


# ---------------------------------------------------------------------------
# Phase 2 — Extract Requirements
# ---------------------------------------------------------------------------

async def extract_requirements(state: DiscoveryState) -> dict:
    """Use requirements agent to identify discrete requirements."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("discovery.extract_requirements")

    result = await discover_requirements(
        llm=llm,
        user_input=state["user_input"],
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
        "phase": "extract_requirements",
    }


# ---------------------------------------------------------------------------
# Phase 3 — Generate Acceptance Criteria
# ---------------------------------------------------------------------------

async def generate_acceptance(state: DiscoveryState) -> dict:
    """For each requirement, generate testable acceptance criteria via LLM."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info(
        "discovery.generate_acceptance",
        requirement_count=len(state.get("requirements", [])),
    )

    requirements = state.get("requirements", [])
    if not requirements:
        return {"phase": "generate_acceptance"}

    # Build prompt for acceptance criteria generation
    req_summaries = "\n".join(
        f"- [{r['id']}] {r['title']}: {r['description']}"
        for r in requirements
    )

    system_prompt = (
        "You are a requirements analyst specialising in OneStream XF financial "
        "consolidation software. Generate specific, testable acceptance criteria "
        "for each requirement. Return criteria as a numbered list per requirement."
    )
    user_message = (
        f"## Requirements\n{req_summaries}\n\n"
        "For each requirement, generate 2-5 concrete, testable acceptance criteria. "
        "Format: REQ-ID: criterion text."
    )

    response = await llm.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.3,
    )

    # Parse criteria back into requirement dicts — enrich existing entries
    updated_requirements: list[dict] = []
    for req in requirements:
        enriched = dict(req)
        # Extract criteria lines referencing this requirement
        criteria_lines = [
            line.strip()
            for line in response.split("\n")
            if req["id"] in line and line.strip()
        ]
        if criteria_lines:
            enriched["acceptance_criteria"] = criteria_lines
        updated_requirements.append(enriched)

    return {
        "requirements": updated_requirements,
        "phase": "generate_acceptance",
    }


# ---------------------------------------------------------------------------
# Phase 4 — Identify Assumptions
# ---------------------------------------------------------------------------

async def identify_assumptions(state: DiscoveryState) -> dict:
    """Flag assumptions that need validation by stakeholders."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("discovery.identify_assumptions")

    requirements = state.get("requirements", [])
    existing_assumptions = state.get("assumptions", [])

    req_summaries = "\n".join(
        f"- [{r['id']}] {r['title']}: {r['description']}"
        for r in requirements
    )

    system_prompt = (
        "You are a requirements analyst for OneStream XF. Identify implicit "
        "assumptions in these requirements that need stakeholder validation. "
        "Consider: data sources, business rules, security, timing, dimensions."
    )
    user_message = (
        f"## User Request\n{state.get('user_input', '')}\n\n"
        f"## Extracted Requirements\n{req_summaries}\n\n"
        f"## Already Identified Assumptions\n"
        + ("\n".join(f"- {a}" for a in existing_assumptions) if existing_assumptions else "None")
        + "\n\nList additional assumptions as bullet points, one per line. "
        "Prefix each with 'ASSUMPTION:'"
    )

    response = await llm.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.3,
    )

    new_assumptions = [
        line.replace("ASSUMPTION:", "").strip()
        for line in response.split("\n")
        if "ASSUMPTION:" in line and line.strip()
    ]

    return {
        "assumptions": new_assumptions,
        "phase": "identify_assumptions",
    }


# ---------------------------------------------------------------------------
# Phase 5 — Gap Analysis
# ---------------------------------------------------------------------------

async def gap_analysis(state: DiscoveryState) -> dict:
    """Check for missing information and generate clarifying questions."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("discovery.gap_analysis")

    requirements = state.get("requirements", [])
    assumptions = state.get("assumptions", [])

    req_summaries = "\n".join(
        f"- [{r['id']}] {r['title']}: {r['description']}"
        for r in requirements
    )

    system_prompt = (
        "You are a senior OneStream XF consultant performing gap analysis on "
        "requirements. Identify missing information, ambiguities, and generate "
        "clarifying questions. Consider: dimension hierarchies, calculation logic, "
        "data mappings, security roles, workflow steps, report layouts."
    )
    user_message = (
        f"## Original Request\n{state.get('user_input', '')}\n\n"
        f"## Extracted Requirements\n{req_summaries}\n\n"
        f"## Assumptions\n"
        + ("\n".join(f"- {a}" for a in assumptions) if assumptions else "None")
        + "\n\nGenerate clarifying questions to fill gaps. "
        "Prefix each with 'QUESTION:'"
    )

    response = await llm.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.3,
    )

    new_questions = [
        line.replace("QUESTION:", "").strip()
        for line in response.split("\n")
        if "QUESTION:" in line and line.strip()
    ]

    return {
        "questions": new_questions,
        "phase": "gap_analysis",
    }


# ---------------------------------------------------------------------------
# Phase 6 — Generate FRD
# ---------------------------------------------------------------------------

async def generate_frd(state: DiscoveryState) -> dict:
    """Produce FRD/TDD section text from all gathered information."""
    llm: LLMClient = state["_llm"]  # type: ignore[typeddict-item]

    logger.info("discovery.generate_frd")

    requirements = state.get("requirements", [])
    assumptions = state.get("assumptions", [])
    questions = state.get("questions", [])

    req_block = "\n".join(
        f"### {r['id']} — {r['title']}\n"
        f"**Description:** {r['description']}\n"
        f"**Priority:** {r.get('priority', 'MEDIUM')}\n"
        f"**Acceptance Criteria:**\n"
        + "\n".join(f"  - {c}" for c in r.get("acceptance_criteria", []))
        for r in requirements
    )

    assumption_block = "\n".join(f"- {a}" for a in assumptions) if assumptions else "None identified."
    question_block = "\n".join(f"- {q}" for q in questions) if questions else "None — requirements appear complete."

    system_prompt = (
        "You are a technical writer producing Functional Requirements Documents "
        "(FRD) for OneStream XF implementations. Write in clear, structured prose "
        "suitable for stakeholder review and sign-off."
    )
    user_message = (
        f"## Requirements\n{req_block}\n\n"
        f"## Assumptions\n{assumption_block}\n\n"
        f"## Open Questions\n{question_block}\n\n"
        "Generate a complete FRD section covering: Overview, Requirements Detail, "
        "Assumptions, Open Items, and Acceptance Criteria Summary."
    )

    frd_text = await llm.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.2,
    )

    return {
        "frd_section": frd_text,
        "phase": "generate_frd",
    }


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_discovery_graph() -> StateGraph:
    """Build and compile the 6-phase requirements discovery workflow graph."""
    graph = StateGraph(DiscoveryState)

    # Add nodes
    graph.add_node("gather_context", gather_context)
    graph.add_node("extract_requirements", extract_requirements)
    graph.add_node("generate_acceptance", generate_acceptance)
    graph.add_node("identify_assumptions", identify_assumptions)
    graph.add_node("gap_analysis", gap_analysis)
    graph.add_node("generate_frd", generate_frd)

    # Linear edges through all 6 phases
    graph.add_edge("gather_context", "extract_requirements")
    graph.add_edge("extract_requirements", "generate_acceptance")
    graph.add_edge("generate_acceptance", "identify_assumptions")
    graph.add_edge("identify_assumptions", "gap_analysis")
    graph.add_edge("gap_analysis", "generate_frd")
    graph.add_edge("generate_frd", END)

    # Entry point
    graph.set_entry_point("gather_context")

    return graph


# Compile the graph
discovery_graph = build_discovery_graph()
