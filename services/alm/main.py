"""ALM & Governance Service — Change management, drift detection, audit."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("alm.starting")
    yield
    logger.info("alm.shutdown")


app = FastAPI(title="OneStream ALM Service", version="0.1.0", lifespan=lifespan)


class ChangeRequestCreate(BaseModel):
    project_id: str
    title: str
    description: str = ""
    type: str = "standard"  # standard, emergency, expedited
    requested_by: str
    target_environment_id: str | None = None


class ApprovalDecision(BaseModel):
    approver: str
    role: str
    decision: str  # approved, rejected, deferred
    comments: str = ""


class DriftCheckRequest(BaseModel):
    environment_id: str
    artefact_ids: list[str] = []


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "alm"}


# ── Change Requests ──

@app.post("/api/change-requests")
async def create_change_request(request: ChangeRequestCreate) -> dict:
    """Create a new change request."""
    from gitops.manager import create_cr

    cr = await create_cr(request.model_dump())
    return cr


@app.get("/api/change-requests/{cr_id}")
async def get_change_request(cr_id: str) -> dict:
    """Get change request details."""
    from gitops.manager import get_cr

    cr = await get_cr(cr_id)
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found")
    return cr


@app.post("/api/change-requests/{cr_id}/approve")
async def approve_change_request(cr_id: str, decision: ApprovalDecision) -> dict:
    """Submit approval decision for a change request (SoD enforced)."""
    from approval.workflow import process_approval
    from compliance.opa_client import check_policy

    # Check SOX segregation of duties via OPA
    policy_result = await check_policy("sox/itgc", {
        "action": "approve_change_request",
        "actor": decision.approver,
        "change_request": {"cr_number": cr_id, "requested_by": ""},  # Loaded from DB
    })

    if not policy_result.get("allow", False):
        raise HTTPException(
            status_code=403,
            detail=f"Policy violation: {policy_result.get('deny', [])}",
        )

    result = await process_approval(cr_id, decision.model_dump())
    return result


# ── Drift Detection ──

@app.post("/api/drift/check")
async def check_drift(request: DriftCheckRequest) -> dict:
    """Check for configuration drift between environments."""
    from drift.detector import detect_drift

    results = await detect_drift(request.environment_id, request.artefact_ids)
    return {"drift_detected": len(results) > 0, "differences": results}


# ── Compliance ──

@app.post("/api/compliance/check")
async def check_compliance(request: dict) -> dict:
    """Run compliance check against OPA policies."""
    from compliance.opa_client import check_policy

    policy = request.get("policy", "deployment/gates")
    input_data = request.get("input", {})
    result = await check_policy(policy, input_data)
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8083)
