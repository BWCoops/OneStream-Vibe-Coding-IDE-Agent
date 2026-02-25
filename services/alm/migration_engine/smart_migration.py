"""Smart Migration Engine — replaces traditional Extract/Load with intelligent diffing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import structlog

logger = structlog.get_logger()


class MigrationAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SKIP = "skip"


class ArtifactType(str, Enum):
    BUSINESS_RULE = "business_rule"
    DIMENSION = "dimension"
    CUBE = "cube"
    DATA_ADAPTER = "data_adapter"
    DASHBOARD = "dashboard"


@dataclass
class MigrationItem:
    artifact_type: ArtifactType
    artifact_name: str
    action: MigrationAction
    source_hash: str
    target_hash: str | None = None
    diff_summary: str = ""


@dataclass
class MigrationPlan:
    id: str
    source_env: str
    target_env: str
    items: list[MigrationItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved: bool = False
    executed: bool = False

    @property
    def creates(self) -> list[MigrationItem]:
        return [i for i in self.items if i.action == MigrationAction.CREATE]

    @property
    def updates(self) -> list[MigrationItem]:
        return [i for i in self.items if i.action == MigrationAction.UPDATE]

    @property
    def deletes(self) -> list[MigrationItem]:
        return [i for i in self.items if i.action == MigrationAction.DELETE]


class SmartMigrationEngine:
    """Compares source and target environments to produce a minimal migration plan."""

    def __init__(self) -> None:
        self.plans: dict[str, MigrationPlan] = {}

    async def generate_plan(
        self,
        plan_id: str,
        source_env: str,
        target_env: str,
        source_artifacts: dict[str, str],
        target_artifacts: dict[str, str],
    ) -> MigrationPlan:
        """Compare source and target to produce a migration plan.

        Args:
            source_artifacts: mapping of artifact_name -> content_hash
            target_artifacts: mapping of artifact_name -> content_hash
        """
        logger.info(
            "migration.generating_plan",
            source=source_env,
            target=target_env,
            source_count=len(source_artifacts),
            target_count=len(target_artifacts),
        )

        items: list[MigrationItem] = []

        # Items in source but not in target → CREATE
        for name, src_hash in source_artifacts.items():
            if name not in target_artifacts:
                items.append(MigrationItem(
                    artifact_type=ArtifactType.BUSINESS_RULE,
                    artifact_name=name,
                    action=MigrationAction.CREATE,
                    source_hash=src_hash,
                    diff_summary=f"New artifact: {name}",
                ))
            elif target_artifacts[name] != src_hash:
                items.append(MigrationItem(
                    artifact_type=ArtifactType.BUSINESS_RULE,
                    artifact_name=name,
                    action=MigrationAction.UPDATE,
                    source_hash=src_hash,
                    target_hash=target_artifacts[name],
                    diff_summary=f"Modified: {name} (hash changed)",
                ))
            # else: identical → skip

        # Items in target but not in source → potential DELETE
        for name, tgt_hash in target_artifacts.items():
            if name not in source_artifacts:
                items.append(MigrationItem(
                    artifact_type=ArtifactType.BUSINESS_RULE,
                    artifact_name=name,
                    action=MigrationAction.DELETE,
                    source_hash="",
                    target_hash=tgt_hash,
                    diff_summary=f"Removed from source: {name}",
                ))

        plan = MigrationPlan(
            id=plan_id,
            source_env=source_env,
            target_env=target_env,
            items=items,
        )
        self.plans[plan_id] = plan

        logger.info(
            "migration.plan_generated",
            plan_id=plan_id,
            creates=len(plan.creates),
            updates=len(plan.updates),
            deletes=len(plan.deletes),
        )

        return plan

    async def execute_plan(self, plan_id: str) -> dict:
        """Execute a previously approved migration plan."""
        plan = self.plans.get(plan_id)
        if not plan:
            return {"error": f"Plan {plan_id} not found"}
        if not plan.approved:
            return {"error": f"Plan {plan_id} not yet approved"}
        if plan.executed:
            return {"error": f"Plan {plan_id} already executed"}

        logger.info("migration.executing", plan_id=plan_id, item_count=len(plan.items))

        # In production, this would call OneStream MCP servers to apply changes
        plan.executed = True

        return {
            "plan_id": plan_id,
            "status": "executed",
            "items_processed": len(plan.items),
            "creates": len(plan.creates),
            "updates": len(plan.updates),
            "deletes": len(plan.deletes),
        }

    def approve_plan(self, plan_id: str) -> bool:
        """Mark a migration plan as approved."""
        plan = self.plans.get(plan_id)
        if plan:
            plan.approved = True
            return True
        return False
