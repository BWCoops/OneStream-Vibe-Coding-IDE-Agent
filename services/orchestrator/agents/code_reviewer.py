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

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import structlog

from llm_client import LLMClient

logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent.parent / "knowledge-base"


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


def _load_deprecated_apis() -> str:
    """Load the deprecated API registry for context injection."""
    deprecated_path = KNOWLEDGE_DIR / "deprecated-apis" / "dotnet8-deprecated.yml"
    if deprecated_path.exists():
        return deprecated_path.read_text(encoding="utf-8")
    return "No deprecated API registry found."


def _build_review_message(request: ReviewRequest) -> str:
    """Build the comprehensive review prompt."""
    parts: list[str] = []

    parts.append(f"## Source Code to Review\n```{request.language}\n{request.source_code}\n```")
    parts.append(f"\n## Rule Type: {request.rule_type}")
    parts.append(f"\n## Target Runtime: {request.target_runtime}")
    parts.append(f"\n## Original Requirement\n{request.original_requirement}")

    if request.requirement_id:
        parts.append(f"\n## Requirement ID: {request.requirement_id}")

    # Inject deprecated API registry
    deprecated = _load_deprecated_apis()
    parts.append(f"\n## Deprecated API Registry\n{deprecated}")

    if request.test_cases:
        tests = "\n".join(request.test_cases[:5])
        parts.append(f"\n## Generated Test Cases (cross-reference)\n{tests}")

    parts.append(
        "\n## Instructions\n"
        "Perform a comprehensive code review. Check all 7 categories from your checklist. "
        "Return your findings as the specified JSON format. Be strict — this code will run "
        "in production financial systems."
    )

    return "\n".join(parts)


def _parse_review_response(response: str) -> ReviewResult:
    """Parse the LLM's review response into structured findings."""
    # Try to extract JSON from the response
    try:
        # Handle markdown code blocks
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        data = json.loads(json_str)

        findings = []
        for f in data.get("findings", []):
            findings.append(
                ReviewFinding(
                    category=ReviewCategory(f.get("category", "correctness")),
                    severity=ReviewSeverity(f.get("severity", "info")),
                    message=f.get("message", ""),
                    line=f.get("line"),
                    suggestion=f.get("suggestion", ""),
                )
            )

        return ReviewResult(
            passed=data.get("passed", False),
            score=float(data.get("score", 0.0)),
            findings=findings,
            summary=data.get("summary", ""),
            retry_guidance=data.get("retry_guidance", ""),
        )

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("code_reviewer.parse_failed", error=str(e))
        return ReviewResult(
            passed=False,
            score=0.0,
            findings=[
                ReviewFinding(
                    category=ReviewCategory.CORRECTNESS,
                    severity=ReviewSeverity.ERROR,
                    message=f"Failed to parse review response: {e}",
                )
            ],
            summary="Review response parsing failed",
            retry_guidance="Previous review could not be parsed. Regenerate with clearer structure.",
        )


async def review_code(llm: LLMClient, request: ReviewRequest) -> ReviewResult:
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

    system_prompt = (PROMPTS_DIR / "code_reviewer.md").read_text(encoding="utf-8")
    user_message = _build_review_message(request)

    # Use 2x context budget for the reviewer
    response = await llm.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=llm.config.reviewer_max_tokens,
        temperature=0.2,  # Lower temperature for more consistent reviews
    )

    result = _parse_review_response(response)

    logger.info(
        "code_reviewer.complete",
        passed=result.passed,
        score=result.score,
        finding_count=len(result.findings),
        error_count=sum(1 for f in result.findings if f.severity == ReviewSeverity.ERROR),
    )

    return result
