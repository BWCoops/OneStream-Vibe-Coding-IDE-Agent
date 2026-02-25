"""Pipeline execution engine — runs stages in topological order."""

from __future__ import annotations

import asyncio
import os
import time
import uuid

import structlog

from scheduler.dag import topological_sort

logger = structlog.get_logger()

# In-memory execution store (use PostgreSQL in production)
_executions: dict[str, dict] = {}


async def execute_pipeline(pipeline_id: str, parameters: dict) -> str:
    """Start executing a pipeline. Returns execution ID."""
    execution_id = str(uuid.uuid4())

    # Load pipeline definition from database
    definition = await _load_pipeline(pipeline_id)
    if not definition:
        raise ValueError(f"Pipeline {pipeline_id} not found")

    stages = definition.get("stages", [])
    layers = topological_sort(stages)
    stage_map = {s["id"]: s for s in stages}

    _executions[execution_id] = {
        "id": execution_id,
        "pipeline_id": pipeline_id,
        "status": "running",
        "started_at": time.time(),
        "completed_at": None,
        "stage_results": {},
        "current_layer": 0,
        "total_layers": len(layers),
    }

    # Execute layers sequentially, stages within a layer in parallel
    asyncio.create_task(_run_pipeline(execution_id, layers, stage_map, parameters))

    return execution_id


async def _run_pipeline(
    execution_id: str,
    layers: list[list[str]],
    stage_map: dict[str, dict],
    parameters: dict,
) -> None:
    """Execute pipeline layers."""
    try:
        for layer_idx, layer in enumerate(layers):
            _executions[execution_id]["current_layer"] = layer_idx

            # Run all stages in this layer concurrently
            tasks = [
                _execute_stage(execution_id, stage_map[stage_id], parameters)
                for stage_id in layer
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for failures
            for stage_id, result in zip(layer, results):
                if isinstance(result, Exception):
                    _executions[execution_id]["stage_results"][stage_id] = {
                        "status": "failed",
                        "error": str(result),
                    }
                    _executions[execution_id]["status"] = "failed"
                    _executions[execution_id]["completed_at"] = time.time()
                    logger.error("pipeline.stage_failed", execution_id=execution_id, stage_id=stage_id, error=str(result))
                    return
                else:
                    _executions[execution_id]["stage_results"][stage_id] = {
                        "status": "completed",
                        "rows_processed": result.get("rows_processed", 0),
                    }

        _executions[execution_id]["status"] = "completed"
        _executions[execution_id]["completed_at"] = time.time()
        logger.info("pipeline.completed", execution_id=execution_id)

    except Exception as e:
        _executions[execution_id]["status"] = "failed"
        _executions[execution_id]["completed_at"] = time.time()
        logger.error("pipeline.failed", execution_id=execution_id, error=str(e))


async def _execute_stage(execution_id: str, stage: dict, parameters: dict) -> dict:
    """Execute a single pipeline stage."""
    stage_id = stage["id"]
    stage_type = stage.get("type", "EXTRACT")
    connector_type = stage.get("connector", {}).get("type", "unknown")

    logger.info(
        "stage.executing",
        execution_id=execution_id,
        stage_id=stage_id,
        stage_type=stage_type,
        connector_type=connector_type,
    )

    # Load and execute connector
    connector = _get_connector(connector_type)
    result = await connector.execute(stage, parameters)

    # Run validation rules if defined
    validation_rules = stage.get("validation_rules", [])
    for rule in validation_rules:
        await _validate(result, rule)

    return result


def _get_connector(connector_type: str):
    """Get the appropriate connector for a stage."""
    from connectors.base import BaseConnector, MockConnector

    connectors: dict[str, type[BaseConnector]] = {
        # Registered connectors will be imported here
    }

    connector_class = connectors.get(connector_type, MockConnector)
    return connector_class()


async def _validate(result: dict, rule: dict) -> None:
    """Run a data quality validation rule."""
    rule_name = rule.get("name", "unnamed")
    expression = rule.get("expression", "")
    severity = rule.get("severity", "error")

    logger.info("validation.check", rule=rule_name, severity=severity)
    # Validation execution would happen here


async def _load_pipeline(pipeline_id: str) -> dict | None:
    """Load pipeline definition from PostgreSQL."""
    try:
        import asyncpg

        db_url = os.getenv("DATABASE_URL", "postgresql://ide_agent:localdev@localhost:5432/onestream_ide")
        conn = await asyncpg.connect(dsn=db_url)
        try:
            row = await conn.fetchrow(
                "SELECT definition FROM pipelines WHERE id = $1",
                pipeline_id,
            )
            if row:
                import json

                return json.loads(row["definition"])
            return None
        finally:
            await conn.close()
    except Exception as e:
        logger.warning("load_pipeline_failed", error=str(e))
        return None


async def get_execution_status(execution_id: str) -> dict | None:
    """Get the current status of a pipeline execution."""
    return _executions.get(execution_id)
