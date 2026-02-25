"""Self-healing pipeline engine — retry, dead-letter, auto-remediation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import structlog

logger = structlog.get_logger()


class HealingAction(str, Enum):
    RETRY = "retry"
    SKIP = "skip"
    DEAD_LETTER = "dead_letter"
    SUBSTITUTE_DEFAULT = "substitute_default"
    ALERT = "alert"


@dataclass
class HealingEvent:
    stage_id: str
    error_type: str
    error_message: str
    action_taken: HealingAction
    attempt: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_base: float = 2.0
    backoff_max: float = 60.0
    dead_letter_after_exhaustion: bool = True


class SelfHealingEngine:
    """Handles stage failures with configurable retry and remediation."""

    def __init__(self) -> None:
        self.events: list[HealingEvent] = []
        self.dead_letter: list[dict] = []

    async def handle_failure(
        self,
        stage_id: str,
        error: Exception,
        attempt: int,
        retry_policy: RetryPolicy,
    ) -> HealingAction:
        """Determine and execute healing action for a failed stage."""
        error_type = type(error).__name__
        error_msg = str(error)

        logger.warning(
            "healing.failure_detected",
            stage_id=stage_id,
            error_type=error_type,
            attempt=attempt,
            max_attempts=retry_policy.max_attempts,
        )

        if attempt < retry_policy.max_attempts:
            action = HealingAction.RETRY
            backoff = min(
                retry_policy.backoff_base ** attempt,
                retry_policy.backoff_max,
            )
            logger.info("healing.retry", stage_id=stage_id, backoff_seconds=backoff)
            await asyncio.sleep(backoff)
        elif retry_policy.dead_letter_after_exhaustion:
            action = HealingAction.DEAD_LETTER
            self.dead_letter.append({
                "stage_id": stage_id,
                "error_type": error_type,
                "error_message": error_msg,
                "attempts_exhausted": attempt,
                "timestamp": datetime.utcnow().isoformat(),
            })
            logger.error("healing.dead_letter", stage_id=stage_id, total_attempts=attempt)
        else:
            action = HealingAction.ALERT
            logger.error("healing.alert_required", stage_id=stage_id)

        event = HealingEvent(
            stage_id=stage_id,
            error_type=error_type,
            error_message=error_msg,
            action_taken=action,
            attempt=attempt,
            resolved=action == HealingAction.RETRY,
        )
        self.events.append(event)

        return action

    def get_dead_letter_queue(self) -> list[dict]:
        """Return all dead-lettered stage failures."""
        return list(self.dead_letter)

    def get_healing_history(self, stage_id: str | None = None) -> list[HealingEvent]:
        """Return healing events, optionally filtered by stage."""
        if stage_id:
            return [e for e in self.events if e.stage_id == stage_id]
        return list(self.events)
