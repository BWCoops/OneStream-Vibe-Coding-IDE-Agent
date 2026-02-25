"""SLA monitoring and alerting for pipeline executions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

import structlog

logger = structlog.get_logger()


class SLAStatus(str, Enum):
    ON_TRACK = "on_track"
    WARNING = "warning"
    BREACHED = "breached"


@dataclass
class SLADefinition:
    pipeline_id: str
    target_duration_minutes: int
    warning_threshold_pct: float = 0.8  # Warn at 80% of target
    critical_contacts: list[str] = field(default_factory=list)


@dataclass
class SLACheckResult:
    pipeline_id: str
    execution_id: str
    status: SLAStatus
    elapsed_minutes: float
    target_minutes: int
    remaining_minutes: float
    message: str


class SLAMonitor:
    """Monitors pipeline execution times against SLA targets."""

    def __init__(self) -> None:
        self.sla_definitions: dict[str, SLADefinition] = {}
        self.breaches: list[SLACheckResult] = []

    def register_sla(self, sla: SLADefinition) -> None:
        """Register an SLA definition for a pipeline."""
        self.sla_definitions[sla.pipeline_id] = sla
        logger.info(
            "sla.registered",
            pipeline_id=sla.pipeline_id,
            target_minutes=sla.target_duration_minutes,
        )

    def check_sla(
        self,
        pipeline_id: str,
        execution_id: str,
        start_time: datetime,
        current_time: datetime | None = None,
    ) -> SLACheckResult:
        """Check current SLA status for a running execution."""
        current_time = current_time or datetime.utcnow()
        sla = self.sla_definitions.get(pipeline_id)

        if not sla:
            return SLACheckResult(
                pipeline_id=pipeline_id,
                execution_id=execution_id,
                status=SLAStatus.ON_TRACK,
                elapsed_minutes=0,
                target_minutes=0,
                remaining_minutes=0,
                message="No SLA defined for this pipeline",
            )

        elapsed = current_time - start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        remaining = sla.target_duration_minutes - elapsed_minutes
        warning_threshold = sla.target_duration_minutes * sla.warning_threshold_pct

        if elapsed_minutes >= sla.target_duration_minutes:
            status = SLAStatus.BREACHED
            message = (
                f"SLA breached: {elapsed_minutes:.1f}min elapsed, "
                f"target was {sla.target_duration_minutes}min"
            )
        elif elapsed_minutes >= warning_threshold:
            status = SLAStatus.WARNING
            message = (
                f"SLA warning: {remaining:.1f}min remaining of "
                f"{sla.target_duration_minutes}min target"
            )
        else:
            status = SLAStatus.ON_TRACK
            message = f"On track: {remaining:.1f}min remaining"

        result = SLACheckResult(
            pipeline_id=pipeline_id,
            execution_id=execution_id,
            status=status,
            elapsed_minutes=round(elapsed_minutes, 2),
            target_minutes=sla.target_duration_minutes,
            remaining_minutes=round(max(0, remaining), 2),
            message=message,
        )

        if status == SLAStatus.BREACHED:
            self.breaches.append(result)
            logger.error("sla.breached", pipeline_id=pipeline_id, execution_id=execution_id)

        return result

    def get_breaches(self, pipeline_id: str | None = None) -> list[SLACheckResult]:
        """Return SLA breaches, optionally filtered by pipeline."""
        if pipeline_id:
            return [b for b in self.breaches if b.pipeline_id == pipeline_id]
        return list(self.breaches)
