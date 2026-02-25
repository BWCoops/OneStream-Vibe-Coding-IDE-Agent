"""
Generator → Critic → Test loop — LangGraph workflow.

This is the default code generation flow:
1. Planning Agent decomposes the request
2. Code Generator produces VB.NET/C#
3. Code Reviewer (critic, 2x context) validates
4. If review fails → feedback loop to generator (max 3 retries)
5. If review passes → Test Engineer generates tests (parallel)
"""

from dataclasses import dataclass
from typing import Literal
import structlog

logger = structlog.get_logger()

MAX_RETRIES = 3


@dataclass
class CodeGenState:
    """State passed through the LangGraph code generation workflow."""

    requirement: str
    rule_type: str
    target_runtime: str
    project_context: dict
    generated_code: str = ""
    review_passed: bool = False
    review_score: float = 0.0
    review_feedback: str = ""
    retry_count: int = 0
    test_cases: list = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.test_cases is None:
            self.test_cases = []


async def generate_node(state: CodeGenState) -> CodeGenState:
    """Code Generator node — produces VB.NET/C# from requirement."""
    from services.orchestrator.agents.code_generator import generate_code, GenerationRequest, TargetRuntime

    logger.info("graph.generate", retry=state.retry_count)

    request = GenerationRequest(
        requirement=state.requirement,
        rule_type=state.rule_type,
        target_runtime=TargetRuntime(state.target_runtime),
        project_context=state.project_context,
        few_shot_examples=[],  # TODO: Load from knowledge base
    )

    if state.retry_count > 0 and state.review_feedback:
        request.requirement += f"\n\nPrevious review feedback:\n{state.review_feedback}"

    result = await generate_code(request)
    state.generated_code = result.source_code
    return state


async def review_node(state: CodeGenState) -> CodeGenState:
    """Code Reviewer node — validates with 2x context budget."""
    from services.orchestrator.agents.code_reviewer import review_code, ReviewRequest

    logger.info("graph.review", code_length=len(state.generated_code))

    request = ReviewRequest(
        source_code=state.generated_code,
        language="vb.net",
        target_runtime=state.target_runtime,
        rule_type=state.rule_type,
        original_requirement=state.requirement,
    )

    result = await review_code(request)
    state.review_passed = result.passed
    state.review_score = result.score
    state.review_feedback = result.retry_guidance
    return state


def should_retry(state: CodeGenState) -> Literal["generate", "test", "end"]:
    """Route after review: retry generation, proceed to tests, or end."""
    if state.review_passed:
        return "test"
    if state.retry_count < MAX_RETRIES:
        state.retry_count += 1
        return "generate"
    logger.warning("graph.max_retries_reached", score=state.review_score)
    return "end"


async def test_node(state: CodeGenState) -> CodeGenState:
    """Test Engineer node — generates tests for approved code."""
    from services.orchestrator.agents.test_engineer import generate_tests, TestGenerationRequest

    logger.info("graph.test_generation")

    request = TestGenerationRequest(
        source_code=state.generated_code,
        rule_type=state.rule_type,
        requirement=state.requirement,
    )

    state.test_cases = await generate_tests(request)
    return state


# TODO: Wire nodes into LangGraph StateGraph
# graph = StateGraph(CodeGenState)
# graph.add_node("generate", generate_node)
# graph.add_node("review", review_node)
# graph.add_node("test", test_node)
# graph.add_edge("generate", "review")
# graph.add_conditional_edges("review", should_retry)
# graph.set_entry_point("generate")
# compiled = graph.compile()
