"""Data Orchestration Service — Pipeline engine with DAG scheduling."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("data_orchestration.starting")
    yield
    logger.info("data_orchestration.shutdown")


app = FastAPI(
    title="OneStream Data Orchestration",
    version="0.1.0",
    lifespan=lifespan,
)


class ExecuteRequest(BaseModel):
    pipeline_id: str
    parameters: dict = {}


class ValidateRequest(BaseModel):
    definition: dict  # Pipeline JSON definition


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "data-orchestration"}


@app.post("/api/validate")
async def validate_pipeline(request: ValidateRequest) -> dict:
    """Validate a pipeline definition (DAG structure, connectors, etc.)."""
    from scheduler.dag import validate_dag
    from designer.models import Pipeline

    issues = validate_dag(request.definition)
    return {"valid": len(issues) == 0, "issues": issues}


@app.post("/api/execute")
async def execute_pipeline(request: ExecuteRequest) -> dict:
    """Trigger pipeline execution."""
    from scheduler.engine import execute_pipeline

    execution_id = await execute_pipeline(request.pipeline_id, request.parameters)
    return {"execution_id": execution_id, "status": "started"}


@app.get("/api/executions/{execution_id}")
async def get_execution_status(execution_id: str) -> dict:
    """Get the status of a pipeline execution."""
    from scheduler.engine import get_execution_status

    status = await get_execution_status(execution_id)
    if not status:
        raise HTTPException(status_code=404, detail="Execution not found")
    return status


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8082)
