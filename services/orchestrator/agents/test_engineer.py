"""Test Engineer Agent — Test generation and synthetic data creation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import structlog

from llm_client import LLMClient

logger = structlog.get_logger()

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class TestType(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    REGRESSION = "regression"
    UAT = "uat"


@dataclass
class TestCase:
    id: str
    type: TestType
    name: str
    description: str
    test_script: str
    expected_result: str
    synthetic_data: dict | None = None


@dataclass
class TestGenerationRequest:
    source_code: str
    rule_type: str
    requirement: str
    requirement_id: str | None = None
    test_types: list[TestType] = field(default_factory=lambda: [TestType.UNIT])


async def generate_tests(llm: LLMClient, request: TestGenerationRequest) -> list[TestCase]:
    """
    Generate test cases for OneStream business rules.

    Covers:
    - Unit tests: Individual function/method validation
    - Integration tests: End-to-end rule execution
    - Regression tests: Edge cases and boundary conditions
    - UAT tests: Business scenario validation

    Uses synthetic financial data generation for test inputs.
    """
    logger.info(
        "test_engineer.generate",
        rule_type=request.rule_type,
        test_types=[t.value for t in request.test_types],
    )

    system_prompt = (PROMPTS_DIR / "test_engineer.md").read_text(encoding="utf-8")

    user_message = (
        f"## Source Code Under Test\n```\n{request.source_code}\n```\n\n"
        f"## Rule Type: {request.rule_type}\n\n"
        f"## Requirement\n{request.requirement}\n\n"
        f"## Requested Test Types: {', '.join(t.value for t in request.test_types)}\n\n"
        f"Generate test cases as a JSON array. Each test should follow the format from your instructions."
    )

    response = await llm.generate(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=4096,
        temperature=0.3,
    )

    return _parse_test_cases(response)


def _parse_test_cases(response: str) -> list[TestCase]:
    """Parse LLM response into TestCase objects."""
    try:
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        data = json.loads(json_str)
        if not isinstance(data, list):
            data = [data]

        tests = []
        for i, tc in enumerate(data):
            tests.append(
                TestCase(
                    id=tc.get("id", f"TC-{i + 1:03d}"),
                    type=TestType(tc.get("type", "unit")),
                    name=tc.get("name", f"Test {i + 1}"),
                    description=tc.get("description", ""),
                    test_script=tc.get("test_script", tc.get("test_steps", "")),
                    expected_result=tc.get("expected_result", ""),
                    synthetic_data=tc.get("test_data"),
                )
            )
        return tests

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.warning("test_engineer.parse_failed", error=str(e))
        return []
