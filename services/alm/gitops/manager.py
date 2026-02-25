"""Git integration and change request management."""

from __future__ import annotations

import os
import uuid
from datetime import datetime

import structlog

logger = structlog.get_logger()


async def create_cr(data: dict) -> dict:
    """Create a change request in the database."""
    try:
        import asyncpg

        db_url = os.getenv("DATABASE_URL", "postgresql://ide_agent:localdev@localhost:5432/onestream_ide")
        conn = await asyncpg.connect(dsn=db_url)
        try:
            cr_number = f"CR-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            row = await conn.fetchrow(
                """INSERT INTO change_requests
                   (project_id, cr_number, title, description, type, requested_by, target_environment_id)
                   VALUES ($1, $2, $3, $4, $5, $6, $7)
                   RETURNING id, cr_number, title, status, created_at""",
                data["project_id"],
                cr_number,
                data["title"],
                data.get("description", ""),
                data.get("type", "standard"),
                data["requested_by"],
                data.get("target_environment_id"),
            )
            return dict(row)
        finally:
            await conn.close()
    except Exception as e:
        logger.error("create_cr_failed", error=str(e))
        raise


async def get_cr(cr_id: str) -> dict | None:
    """Get change request with approvals."""
    try:
        import asyncpg

        db_url = os.getenv("DATABASE_URL", "postgresql://ide_agent:localdev@localhost:5432/onestream_ide")
        conn = await asyncpg.connect(dsn=db_url)
        try:
            row = await conn.fetchrow(
                """SELECT id, cr_number, title, description, type, status,
                          requested_by, target_environment_id, created_at, updated_at
                   FROM change_requests WHERE id = $1 OR cr_number = $1""",
                cr_id,
            )
            if not row:
                return None

            approvals = await conn.fetch(
                "SELECT approver, role, decision, comments, decided_at FROM approvals WHERE change_request_id = $1",
                row["id"],
            )

            result = dict(row)
            result["approvals"] = [dict(a) for a in approvals]
            return result
        finally:
            await conn.close()
    except Exception as e:
        logger.error("get_cr_failed", error=str(e))
        return None
