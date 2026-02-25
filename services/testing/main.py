"""Testing Service — Test execution engine with DeepEval integration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("testing.starting")
    yield
    logger.info("testing.shutdown")


app = FastAPI(title="OneStream Testing Service", version="0.1.0", lifespan=lifespan)


class RunTestsRequest(BaseModel):
    artefact_id: str
    test_type: str = "unit"  # unit, integration, regression, uat
    source_code: str = ""
    test_cases: list[dict] = []


class EvalRequest(BaseModel):
    generated_code: str
    requirement: str
    rule_type: str


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "testing"}


@app.post("/api/run")
async def run_tests(request: RunTestsRequest) -> dict:
    """Execute test cases against an artefact."""
    from runners.executor import execute_tests

    results = await execute_tests(
        artefact_id=request.artefact_id,
        test_type=request.test_type,
        source_code=request.source_code,
        test_cases=request.test_cases,
    )
    return results


@app.post("/api/evaluate")
async def evaluate_output(request: EvalRequest) -> dict:
    """Evaluate LLM-generated code using DeepEval metrics."""
    from deepeval_integration.evaluator import evaluate_code

    result = await evaluate_code(
        generated_code=request.generated_code,
        requirement=request.requirement,
        rule_type=request.rule_type,
    )
    return result


@app.post("/api/generate-synthetic")
async def generate_synthetic_data(request: dict) -> dict:
    """Generate synthetic financial data for testing."""
    from synthetic.generator import generate_synthetic

    data = await generate_synthetic(
        data_type=request.get("data_type", "financial"),
        row_count=request.get("row_count", 100),
        schema=request.get("schema", {}),
    )
    return data


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8084)
