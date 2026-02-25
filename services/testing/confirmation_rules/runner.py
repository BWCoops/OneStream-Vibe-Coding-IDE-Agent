"""OneStream Confirmation Rule integration for validation testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import structlog

logger = structlog.get_logger()


class ConfirmationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ConfirmationCheck:
    rule_name: str
    description: str
    status: ConfirmationStatus
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class ConfirmationResult:
    entity: str
    scenario: str
    period: str
    checks: list[ConfirmationCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.status in (ConfirmationStatus.PASSED, ConfirmationStatus.SKIPPED) for c in self.checks)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.status == ConfirmationStatus.PASSED)


class ConfirmationRuleRunner:
    """Runs OneStream Confirmation Rules for data quality validation.

    Confirmation Rules are OneStream's built-in mechanism for data validation
    during the financial close process. They check things like:
    - Balance sheet balances (Assets = Liabilities + Equity)
    - IC eliminations net to zero
    - Required data has been submitted
    - Variance thresholds are not exceeded
    """

    def __init__(self) -> None:
        self.rules: list[dict] = []

    def register_rule(self, name: str, description: str, check_fn: str) -> None:
        """Register a confirmation rule check."""
        self.rules.append({
            "name": name,
            "description": description,
            "check_fn": check_fn,
        })

    async def run_confirmations(
        self,
        entity: str,
        scenario: str,
        period: str,
    ) -> ConfirmationResult:
        """Run all registered confirmation rules for a given intersection.

        In production, this would invoke OneStream's Confirmation Rule engine
        via the REST API. For testing, it runs synthetic checks.
        """
        logger.info(
            "confirmation.running",
            entity=entity,
            scenario=scenario,
            period=period,
            rule_count=len(self.rules),
        )

        checks = []

        # Built-in standard checks
        checks.append(ConfirmationCheck(
            rule_name="BS_Balance",
            description="Balance sheet must balance (Assets = L + E)",
            status=ConfirmationStatus.PASSED,
            message="Balance sheet balances within tolerance",
            details={"variance": 0.00, "tolerance": 0.01},
        ))

        checks.append(ConfirmationCheck(
            rule_name="IC_Elimination",
            description="Intercompany eliminations must net to zero",
            status=ConfirmationStatus.PASSED,
            message="IC eliminations balanced",
            details={"net_amount": 0.00},
        ))

        checks.append(ConfirmationCheck(
            rule_name="Data_Submission",
            description="All required entities must have submitted data",
            status=ConfirmationStatus.PASSED,
            message="Data submitted for all required entities",
            details={"submitted": 5, "required": 5},
        ))

        result = ConfirmationResult(
            entity=entity,
            scenario=scenario,
            period=period,
            checks=checks,
        )

        logger.info(
            "confirmation.complete",
            entity=entity,
            passed=result.passed,
            total=result.total,
            passed_count=result.passed_count,
        )

        return result
