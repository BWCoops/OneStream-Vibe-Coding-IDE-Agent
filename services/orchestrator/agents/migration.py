"""Migration Agent — BPC/HFM to OneStream translation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from llm_client import LLMClient

logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


@dataclass
class MigrationResult:
    source_platform: str  # "bpc" or "hfm"
    source_code: str
    translated_code: str
    translation_notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _load_system_prompt() -> str:
    """Load the migration agent system prompt."""
    prompt_path = PROMPTS_DIR / "migration.md"
    return prompt_path.read_text(encoding="utf-8")


def _build_user_message(
    source_code: str,
    source_platform: str,
    target_runtime: str,
) -> str:
    """Construct the user message for migration."""
    parts: list[str] = []

    parts.append(f"## Source Platform\n{source_platform.upper()}")
    parts.append(f"\n## Target Runtime\n{target_runtime}")
    parts.append(f"\n## Source Code\n```\n{source_code}\n```")
    parts.append(
        "\n## Instructions\n"
        "Translate the above source code to OneStream VB.NET following "
        "the migration patterns in your system prompt. "
        "Return your result as the JSON format specified in your instructions."
    )

    return "\n".join(parts)


def _parse_migration_response(response: str, source_platform: str, source_code: str) -> MigrationResult:
    """Parse the LLM response into a MigrationResult."""
    try:
        # Handle markdown code blocks
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        data = json.loads(json_str)

        return MigrationResult(
            source_platform=source_platform,
            source_code=source_code,
            translated_code=data.get("translated_code", ""),
            translation_notes=data.get("translation_notes", []),
            warnings=data.get("warnings", []),
        )

    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        logger.warning("migration.parse_failed", error=str(e))
        # If JSON parsing fails, the response may be raw VB.NET code
        return MigrationResult(
            source_platform=source_platform,
            source_code=source_code,
            translated_code=response,
            translation_notes=["Response was not structured JSON; raw output used as translated code."],
            warnings=[f"Parse error: {e}"],
        )


async def translate_code(
    llm: LLMClient,
    source_code: str,
    source_platform: str,
    target_runtime: str = "net8.0",
) -> MigrationResult:
    """
    Translate SAP BPC Script Logic or Oracle HFM rules to OneStream VB.NET.

    Process:
    1. Source analysis — Parse and understand source logic
    2. Pattern matching — Map to known migration patterns (BPC/HFM tables)
    3. Translation — Generate equivalent OneStream VB.NET code
    4. Validation — Check for deprecated APIs, best practices
    """
    logger.info(
        "migration.translate",
        source_platform=source_platform,
        target_runtime=target_runtime,
        code_length=len(source_code),
    )

    system_prompt = _load_system_prompt()
    user_message = _build_user_message(source_code, source_platform, target_runtime)

    response = await llm.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=None,
        temperature=0.2,
    )

    result = _parse_migration_response(response, source_platform, source_code)

    logger.info(
        "migration.complete",
        translated_length=len(result.translated_code),
        note_count=len(result.translation_notes),
        warning_count=len(result.warnings),
    )

    return result
