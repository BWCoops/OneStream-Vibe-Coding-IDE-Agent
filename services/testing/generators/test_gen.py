"""Test case generators for unit, integration, regression, and UAT tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import structlog

logger = structlog.get_logger()


class TestType(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    REGRESSION = "regression"
    UAT = "uat"


@dataclass
class GeneratedTestCase:
    id: str
    name: str
    test_type: TestType
    description: str
    setup: str
    steps: list[str]
    expected_result: str
    teardown: str = ""
    tags: list[str] = field(default_factory=list)


class TestCaseGenerator:
    """Generates test case templates for OneStream business rules."""

    def generate_unit_tests(self, rule_source: str, rule_type: str) -> list[GeneratedTestCase]:
        """Generate unit test cases for a business rule."""
        tests = []

        # Error handling test
        tests.append(GeneratedTestCase(
            id="UT-001",
            name="Error handling coverage",
            test_type=TestType.UNIT,
            description="Verify that all code paths have proper Try/Catch/Finally blocks",
            setup="Load business rule source code",
            steps=[
                "Parse source for Try/Catch blocks",
                "Verify BRApi.ErrorLog.LogMessage is called in Catch blocks",
                "Verify step identification in error messages",
                "Check Finally block exists for cleanup",
            ],
            expected_result="All execution paths covered by error handling",
            tags=["error-handling", "mandatory"],
        ))

        # Null/empty input test
        tests.append(GeneratedTestCase(
            id="UT-002",
            name="Null and empty input handling",
            test_type=TestType.UNIT,
            description="Verify rule handles null/empty inputs gracefully",
            setup="Prepare test context with null dimension members",
            steps=[
                "Pass null entity to rule",
                "Pass empty account string",
                "Pass zero-value amount",
            ],
            expected_result="Rule handles gracefully without unhandled exceptions",
            tags=["boundary", "null-safety"],
        ))

        # Deprecated API check
        tests.append(GeneratedTestCase(
            id="UT-003",
            name="No deprecated API usage",
            test_type=TestType.UNIT,
            description="Verify rule does not use deprecated OneStream APIs",
            setup="Load deprecated API registry for target platform version",
            steps=[
                "Scan source for BRApi.Utilities.EncryptText",
                "Scan source for BRApi.Utilities.DecryptText",
                "Scan source for System.Data.SqlClient on .NET 8",
                "Scan source for WinSCP references",
            ],
            expected_result="No deprecated API usage detected",
            tags=["deprecated-api", "compliance"],
        ))

        if rule_type == "finance_rule":
            tests.append(GeneratedTestCase(
                id="UT-004",
                name="IC elimination balance",
                test_type=TestType.UNIT,
                description="Verify intercompany eliminations net to zero",
                setup="Prepare IC transaction pairs between entities",
                steps=[
                    "Generate IC Revenue and IC COGS entries",
                    "Execute IC elimination logic",
                    "Sum all elimination entries",
                ],
                expected_result="Net elimination amount equals zero",
                tags=["ic-elimination", "finance"],
            ))

        logger.info("test_gen.unit_tests", count=len(tests), rule_type=rule_type)
        return tests

    def generate_integration_tests(self, rule_type: str) -> list[GeneratedTestCase]:
        """Generate integration test cases."""
        tests = []

        tests.append(GeneratedTestCase(
            id="IT-001",
            name="Dimension member resolution",
            test_type=TestType.INTEGRATION,
            description="Verify rule correctly resolves dimension members via BRApi",
            setup="Configure test environment with known dimension hierarchy",
            steps=[
                "Call BRApi.Finance.Members.GetMemberId for test entity",
                "Verify member ID is valid and non-zero",
                "Call GetBaseMembers for parent member",
                "Verify child members returned correctly",
            ],
            expected_result="All dimension member lookups resolve correctly",
            tags=["dimensions", "brapi"],
        ))

        tests.append(GeneratedTestCase(
            id="IT-002",
            name="Data write and read-back",
            test_type=TestType.INTEGRATION,
            description="Verify data written by rule can be read back correctly",
            setup="Clear test data intersection",
            steps=[
                "Execute rule with known input data",
                "Read data back from the target intersection",
                "Compare written values with expected values",
            ],
            expected_result="Written data matches expected values exactly",
            tags=["data-integrity", "brapi"],
        ))

        return tests

    def generate_regression_tests(self, baseline_results: dict) -> list[GeneratedTestCase]:
        """Generate regression tests based on known-good baseline."""
        tests = []

        tests.append(GeneratedTestCase(
            id="RT-001",
            name="Output consistency with baseline",
            test_type=TestType.REGRESSION,
            description="Verify rule outputs match established baseline within tolerance",
            setup="Load baseline result set",
            steps=[
                "Execute rule with baseline input parameters",
                "Compare each output value against baseline",
                "Check variance is within 0.01% tolerance",
            ],
            expected_result="All outputs within tolerance of baseline values",
            tags=["regression", "baseline"],
        ))

        return tests
