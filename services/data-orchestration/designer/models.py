"""Data Orchestration Pipeline models — matches CLAUDE.md spec."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StageType(str, Enum):
    EXTRACT = "EXTRACT"
    TRANSFORM = "TRANSFORM"
    VALIDATE = "VALIDATE"
    LOAD = "LOAD"


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 2.0
    backoff_multiplier: float = 2.0
    dead_letter_queue: str = ""


@dataclass
class SLADefinition:
    target_minutes: int
    warning_threshold_pct: float = 80.0
    alert_channels: list[str] = field(default_factory=list)


@dataclass
class ConnectorConfig:
    type: str  # 'sql_server', 'csv', 'sftp', 'rest', etc.
    connection_string: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationRule:
    name: str
    expression: str
    severity: str = "error"


@dataclass
class Stage:
    id: str
    type: StageType
    connector: ConnectorConfig
    dependencies: list[str] = field(default_factory=list)
    transformation: str = ""
    validation_rules: list[ValidationRule] = field(default_factory=list)


@dataclass
class Schedule:
    type: str  # 'cron', 'event', 'conditional'
    expression: str = ""
    event_source: str = ""


@dataclass
class LineageMapping:
    source_column: str
    source_stage: str
    target_column: str
    target_stage: str
    transformation: str = ""


@dataclass
class LineageGraph:
    mappings: list[LineageMapping] = field(default_factory=list)


@dataclass
class Pipeline:
    id: str
    name: str
    description: str
    stages: list[Stage] = field(default_factory=list)
    schedule: Schedule | None = None
    sla: SLADefinition | None = None
    lineage: LineageGraph = field(default_factory=LineageGraph)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
