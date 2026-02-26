"""Requirements Analyst Agent — Discovery, FRD/TDD generation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from llm_client import LLMClient

logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


@dataclass
class Requirement:
    id: str
    category: str
    title: str
    description: str
    acceptance_criteria: list[str] = field(default_factory=list)
    priority: str = "MEDIUM"


@dataclass
class DiscoveryResult:
    requirements: list[Requirement]
    assumptions: list[str]
    questions: list[str]
    frd_section: str


def _load_system_prompt() -> str:
    """Load the requirements analyst system prompt."""
    prompt_path = PROMPTS_DIR / "requirements.md"
    return prompt_path.read_text(encoding="utf-8")


def _build_user_message(user_input: str, project_context: dict) -> str:
    """Construct the user message with the input and project context."""
    parts: list[str] = []

    parts.append(f"## User Input\n{user_input}")

    if project_context:
        ctx = "\n".join(f"- {k}: {v}" for k, v in project_context.items())
        parts.append(f"\n## Project Context\n{ctx}")

    parts.append(
        "\n## Instructions\n"
        "Perform the full 6-phase discovery process on the above input. "
        "Return your analysis as the JSON format specified in your system prompt."
    )

    return "\n".join(parts)


def _parse_discovery_response(response: str) -> DiscoveryResult:
    """Parse the LLM JSON response into a DiscoveryResult."""
    try:
        # Handle markdown code blocks
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        data = json.loads(json_str)

        requirements = []
        for r in data.get("requirements", []):
            requirements.append(
                Requirement(
                    id=r.get("id", f"REQ-{len(requirements) + 1:03d}"),
                    category=r.get("category", "FUNCTIONAL"),
                    title=r.get("title", ""),
                    description=r.get("description", ""),
                    acceptance_criteria=r.get("acceptance_criteria", []),
                    priority=r.get("priority", "MEDIUM"),
                )
            )

        return DiscoveryResult(
            requirements=requirements,
            assumptions=data.get("assumptions", []),
            questions=data.get("questions", []),
            frd_section=data.get("frd_section", ""),
        )

    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        logger.warning("requirements.parse_failed", error=str(e))
        return DiscoveryResult(
            requirements=[],
            assumptions=[],
            questions=[f"Failed to parse requirements: {e}"],
            frd_section="",
        )


async def discover_requirements(
    llm: LLMClient,
    user_input: str,
    project_context: dict,
) -> DiscoveryResult:
    """
    6-phase requirements discovery process:
    1. Context gathering — Understand the business scenario
    2. Requirement extraction — Identify discrete requirements
    3. Acceptance criteria — Define testable criteria per requirement
    4. Assumption identification — Flag assumptions for validation
    5. Gap analysis — Identify missing information
    6. Document generation — Produce FRD/TDD sections

    The LLM performs all six phases in a single pass using the
    comprehensive system prompt that structures the output.
    """
    logger.info("requirements.discover", input_length=len(user_input))

    system_prompt = _load_system_prompt()
    user_message = _build_user_message(user_input, project_context)

    response = await llm.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=None,
        temperature=0.3,
    )

    result = _parse_discovery_response(response)

    logger.info(
        "requirements.complete",
        requirement_count=len(result.requirements),
        assumption_count=len(result.assumptions),
        question_count=len(result.questions),
    )

    return result
