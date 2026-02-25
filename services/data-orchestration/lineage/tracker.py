"""Column-level data lineage tracking."""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class ColumnLineage:
    """Tracks the lineage of a single column through the pipeline."""

    source_stage: str
    source_column: str
    target_stage: str
    target_column: str
    transformation: str = ""  # SQL expression or description


@dataclass
class LineageGraph:
    """Complete lineage graph for a pipeline execution."""

    pipeline_id: str
    execution_id: str
    mappings: list[ColumnLineage] = field(default_factory=list)

    def add_mapping(
        self,
        source_stage: str,
        source_column: str,
        target_stage: str,
        target_column: str,
        transformation: str = "",
    ) -> None:
        self.mappings.append(
            ColumnLineage(
                source_stage=source_stage,
                source_column=source_column,
                target_stage=target_stage,
                target_column=target_column,
                transformation=transformation,
            )
        )

    def get_upstream(self, stage_id: str, column: str) -> list[ColumnLineage]:
        """Get all upstream sources for a given column."""
        return [m for m in self.mappings if m.target_stage == stage_id and m.target_column == column]

    def get_downstream(self, stage_id: str, column: str) -> list[ColumnLineage]:
        """Get all downstream targets for a given column."""
        return [m for m in self.mappings if m.source_stage == stage_id and m.source_column == column]

    def to_dict(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "execution_id": self.execution_id,
            "mappings": [
                {
                    "source_stage": m.source_stage,
                    "source_column": m.source_column,
                    "target_stage": m.target_stage,
                    "target_column": m.target_column,
                    "transformation": m.transformation,
                }
                for m in self.mappings
            ],
        }


def extract_lineage_from_sql(sql: str, source_stage: str, target_stage: str) -> list[ColumnLineage]:
    """
    Parse SQL transformation to extract column-level lineage.

    Handles basic SELECT ... FROM patterns. For complex SQL,
    falls back to noting the entire expression.
    """
    lineage: list[ColumnLineage] = []

    # Basic heuristic: extract column names from SELECT clause
    sql_upper = sql.upper().strip()
    if "SELECT" in sql_upper and "FROM" in sql_upper:
        select_part = sql[sql_upper.index("SELECT") + 6 : sql_upper.index("FROM")].strip()
        columns = [c.strip() for c in select_part.split(",")]

        for col_expr in columns:
            parts = col_expr.split(" AS ")
            source_col = parts[0].strip()
            target_col = parts[-1].strip() if len(parts) > 1 else source_col

            # Remove table alias prefix
            if "." in source_col:
                source_col = source_col.split(".")[-1]
            if "." in target_col:
                target_col = target_col.split(".")[-1]

            lineage.append(
                ColumnLineage(
                    source_stage=source_stage,
                    source_column=source_col,
                    target_stage=target_stage,
                    target_column=target_col,
                    transformation=col_expr if len(parts) > 1 or "(" in col_expr else "",
                )
            )

    return lineage
