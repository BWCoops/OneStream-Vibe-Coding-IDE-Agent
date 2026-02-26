"""Data Orchestration Agent — Pipeline design and DAG generation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from llm_client import LLMClient

logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


@dataclass
class PipelineDesign:
    name: str
    description: str
    stages: list[dict]
    schedule: dict | None = None
    sla_target_minutes: int | None = None
    generated_adapter_code: str = ""


def _load_system_prompt() -> str:
    """Load the data orchestration agent system prompt."""
    prompt_path = PROMPTS_DIR / "data_orchestration.md"
    return prompt_path.read_text(encoding="utf-8")


def _build_user_message(user_request: str, project_context: dict) -> str:
    """Construct the user message for pipeline design."""
    parts: list[str] = []

    parts.append(f"## User Request\n{user_request}")

    if project_context:
        ctx = "\n".join(f"- {k}: {v}" for k, v in project_context.items())
        parts.append(f"\n## Project Context\n{ctx}")

    parts.append(
        "\n## Instructions\n"
        "Design a complete data pipeline based on the above request. "
        "Include all stages (EXTRACT, TRANSFORM, VALIDATE, LOAD), "
        "connector configurations, validation rules, and the generated "
        "OneStream Data Adapter business rule code. "
        "Return your design as the JSON format specified in your system prompt."
    )

    return "\n".join(parts)


def _parse_pipeline_response(response: str) -> PipelineDesign:
    """Parse the LLM response into a PipelineDesign."""
    try:
        # Handle markdown code blocks
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        data = json.loads(json_str)

        schedule = data.get("schedule")
        sla = data.get("sla_target_minutes")

        return PipelineDesign(
            name=data.get("name", "Untitled Pipeline"),
            description=data.get("description", ""),
            stages=data.get("stages", []),
            schedule=schedule if isinstance(schedule, dict) else None,
            sla_target_minutes=int(sla) if sla is not None else None,
            generated_adapter_code=data.get("generated_adapter_code", ""),
        )

    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        logger.warning("data_orchestration.parse_failed", error=str(e))
        return PipelineDesign(
            name="Parse Error",
            description=f"Failed to parse pipeline design: {e}",
            stages=[],
        )


async def design_pipeline(
    llm: LLMClient,
    user_request: str,
    project_context: dict,
) -> PipelineDesign:
    """
    Design a data orchestration pipeline from natural language description.

    Generates:
    - Pipeline DAG with stages and dependencies
    - Connector configurations per stage
    - Transformation logic (SQL/Python/VB.NET)
    - Validation rules for data quality
    - OneStream Data Adapter business rule code
    """
    logger.info("data_orchestration.design", request_length=len(user_request))

    system_prompt = _load_system_prompt()
    user_message = _build_user_message(user_request, project_context)

    response = await llm.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=None,
        temperature=0.3,
    )

    result = _parse_pipeline_response(response)

    logger.info(
        "data_orchestration.complete",
        pipeline_name=result.name,
        stage_count=len(result.stages),
        has_adapter_code=bool(result.generated_adapter_code),
    )

    return result
