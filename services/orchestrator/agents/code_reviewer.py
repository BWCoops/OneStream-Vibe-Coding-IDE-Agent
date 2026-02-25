"""
Code Reviewer (Verification) Agent — The MOST IMPORTANT agent.

This agent receives 2x the context window budget of the generator.
It validates generated code against:
- OneStream API correctness
- Best-practice conformance
- Deprecated API detection
- Security analysis
- Performance patterns
- Error handling completeness
- Requirement cross-reference (RTM)
"""

from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class ReviewSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


class ReviewCategory(str, Enum):
    CORRECTNESS = "correctness"
    BEST_PRACTICE = "best_practice"
    DEPRECATED_API = "deprecated_api"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ERROR_HANDLING = "error_handling"
    REQUIREMENT_COVERAGE = "requirement_coverage"


@dataclass
class ReviewFinding:
    category: ReviewCategory
    severity: ReviewSeverity
    message: str
    line: int | None = None
    suggestion: str = ""


@dataclass
class ReviewResult:
    passed: bool
    score: float  # 0.0 to 1.0
    findings: list[ReviewFinding] = field(default_factory=list)
    summary: str = ""
    retry_guidance: str = ""  # Feedback for the generator on retry


@dataclass
class ReviewRequest:
    source_code: str
    language: str
    target_runtime: str
    rule_type: str
    original_requirement: str
    requirement_id: str | None = None
    test_cases: list[str] = field(default_factory=list)


async def review_code(request: ReviewRequest) -> ReviewResult:
    """
    Comprehensive code review using 2x context budget.

    The reviewer receives:
    - Full source code
    - OneStream API reference for the target platform version
    - Deprecated API registry
    - Best-practice compliance checklist
    - The original requirement (RTM cross-reference)
    - Generated test cases

    Checks performed:
    1. Correctness — Does the code fulfill the requirement?
    2. Best-practice conformance — OneStream certified patterns
    3. Deprecated API usage — Per-version deprecated API registry
    4. Security — Hardcoded creds, SQL injection, input validation
    5. Performance — Row-by-row vs bulk, unnecessary loops
    6. Error handling — Try/Catch/Finally, BRApi.ErrorLog usage
    7. Requirement coverage — All acceptance criteria addressed
    """
    logger.info(
        "code_reviewer.review",
        code_length=len(request.source_code),
        rule_type=request.rule_type,
        runtime=request.target_runtime,
    )

    # TODO: Implement LLM-based review with 2x context budget
    # 1. Load system prompt from prompts/code_reviewer.md
    # 2. Load deprecated API registry
    # 3. Load best-practice checklist
    # 4. Build review prompt (2x context allocation)
    # 5. Call LLM with structured output
    # 6. Parse findings and compute score

    return ReviewResult(
        passed=False,
        score=0.0,
        findings=[],
        summary="Code review not yet implemented",
        retry_guidance="",
    )
