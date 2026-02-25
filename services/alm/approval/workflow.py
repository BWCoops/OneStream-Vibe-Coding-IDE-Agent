"""Approval workflow engine with segregation of duties enforcement."""

from __future__ import annotations

import os

import structlog

logger = structlog.get_logger()


async def process_approval(cr_id: str, decision: dict) -> dict:
    """Process an approval decision and update the change request status."""
    try:
        import asyncpg

        db_url = os.getenv("DATABASE_URL", "postgresql://ide_agent:localdev@localhost:5432/onestream_ide")
        conn = await asyncpg.connect(dsn=db_url)
        try:
            # Get the change request
            cr = await conn.fetchrow(
                "SELECT id, requested_by, status FROM change_requests WHERE id = $1 OR cr_number = $1",
                cr_id,
            )
            if not cr:
                return {"error": "Change request not found"}

            # Segregation of Duties: approver != requester
            if decision["approver"] == cr["requested_by"]:
                return {"error": "SOX SoD violation: cannot approve own change request"}

            # Record the approval
            await conn.execute(
                """INSERT INTO approvals (change_request_id, approver, role, decision, comments)
                   VALUES ($1, $2, $3, $4, $5)""",
                cr["id"],
                decision["approver"],
                decision["role"],
                decision["decision"],
                decision.get("comments", ""),
            )

            # Update CR status based on decision
            new_status = cr["status"]
            if decision["decision"] == "approved":
                new_status = "approved"
            elif decision["decision"] == "rejected":
                new_status = "rejected"

            await conn.execute(
                "UPDATE change_requests SET status = $1, updated_at = NOW() WHERE id = $2",
                new_status,
                cr["id"],
            )

            # Audit log
            await conn.execute(
                """INSERT INTO audit_log (event_type, entity_type, entity_id, actor, action, details, entry_hash)
                   VALUES ('approval', 'change_request', $1, $2, $3, $4,
                           encode(sha256(($5 || $1 || $3)::bytea), 'hex'))""",
                str(cr["id"]),
                decision["approver"],
                decision["decision"],
                f'{{"role": "{decision["role"]}", "comments": "{decision.get("comments", "")}"}}',
                str(os.getpid()),
            )

            return {
                "cr_id": str(cr["id"]),
                "status": new_status,
                "decision": decision["decision"],
                "approver": decision["approver"],
            }
        finally:
            await conn.close()
    except Exception as e:
        logger.error("process_approval_failed", error=str(e))
        return {"error": str(e)}
