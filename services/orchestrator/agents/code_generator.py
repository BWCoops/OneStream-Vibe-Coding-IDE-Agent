"""Code Generator Agent — VB.NET/C# generation for OneStream business rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import structlog

from llm_client import LLMClient

logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class TargetRuntime(str, Enum):
    NET8 = "net8.0"
    NET48 = "net48"


@dataclass
class GenerationRequest:
    requirement: str
    rule_type: str
    target_runtime: TargetRuntime
    project_context: dict
    few_shot_examples: list[str] = field(default_factory=list)
    retry_feedback: str = ""


@dataclass
class GenerationResult:
    source_code: str
    language: str  # "vb.net" or "csharp"
    target_runtime: TargetRuntime
    explanation: str
    confidence: float


def _load_system_prompt(target_runtime: TargetRuntime) -> str:
    """Load and customize the code generator system prompt."""
    prompt_path = PROMPTS_DIR / "code_generator.md"
    prompt = prompt_path.read_text(encoding="utf-8")

    if target_runtime == TargetRuntime.NET48:
        prompt += "\n\n## LEGACY MODE\nTarget .NET Framework 4.8. The deprecated API restrictions do NOT apply."

    return prompt


def _build_user_message(request: GenerationRequest) -> str:
    """Construct the user message with requirement, examples, and context."""
    parts: list[str] = []

    parts.append(f"## Requirement\n{request.requirement}")
    parts.append(f"\n## Rule Type\n{request.rule_type}")
    parts.append(f"\n## Target Runtime\n{request.target_runtime.value}")

    if request.project_context:
        ctx = "\n".join(f"- {k}: {v}" for k, v in request.project_context.items())
        parts.append(f"\n## Project Context\n{ctx}")

    if request.few_shot_examples:
        examples = "\n---\n".join(request.few_shot_examples[:3])
        parts.append(f"\n## Reference Examples\n{examples}")

    if request.retry_feedback:
        parts.append(f"\n## Previous Review Feedback (FIX THESE ISSUES)\n{request.retry_feedback}")

    parts.append("\n## Instructions\nGenerate the complete business rule code. Return ONLY the source code.")

    return "\n".join(parts)


async def generate_code(llm: LLMClient, request: GenerationRequest) -> GenerationResult:
    """
    Generate OneStream business rule code from requirements.

    Uses LLM with:
    - System prompt containing OneStream coding standards
    - Few-shot examples from knowledge-base/code-patterns/
    - Platform-version-aware generation (NET 8 vs legacy)
    - Structured Try/Catch/Finally per coding standards
    """
    logger.info(
        "code_generator.generate",
        rule_type=request.rule_type,
        runtime=request.target_runtime.value,
        has_retry_feedback=bool(request.retry_feedback),
    )

    system_prompt = _load_system_prompt(request.target_runtime)
    user_message = _build_user_message(request)

    source_code = await llm.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=None,  # Uses default generator tokens
        temperature=0.3,
    )

    # Strip markdown code fences if present
    if source_code.startswith("```"):
        lines = source_code.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        source_code = "\n".join(lines)

    language = "vb.net" if "Sub Main" in source_code or "Function Main" in source_code else "csharp"

    logger.info(
        "code_generator.complete",
        language=language,
        code_length=len(source_code),
    )

    return GenerationResult(
        source_code=source_code,
        language=language,
        target_runtime=request.target_runtime,
        explanation="Generated from requirement via LLM",
        confidence=0.85,
    )
