"""Immutable audit trail with hash chaining — SOX/DORA compliance."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime

import structlog

logger = structlog.get_logger()


async def append_audit_entry(
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor: str,
    action: str,
    details: dict | None = None,
) -> dict:
    """
    Append an immutable audit log entry with hash chaining.

    Each entry's hash includes the previous entry's hash,
    forming a tamper-evident chain (similar to blockchain).
    """
    try:
        import asyncpg

        db_url = os.getenv("DATABASE_URL", "postgresql://ide_agent:localdev@localhost:5432/onestream_ide")
        conn = await asyncpg.connect(dsn=db_url)
        try:
            # Get the hash of the last entry for chain linking
            last = await conn.fetchrow(
                "SELECT id, entry_hash FROM audit_log ORDER BY id DESC LIMIT 1"
            )
            previous_hash = last["entry_hash"] if last else None

            # Compute this entry's hash (includes previous hash for chain integrity)
            details_json = json.dumps(details or {}, sort_keys=True)
            hash_input = f"{previous_hash or ''}|{event_type}|{entity_type}|{entity_id}|{actor}|{action}|{details_json}"
            entry_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

            row = await conn.fetchrow(
                """INSERT INTO audit_log
                   (event_type, entity_type, entity_id, actor, action, details, previous_hash, entry_hash)
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
                   RETURNING id, event_type, entity_id, actor, action, entry_hash, created_at""",
                event_type,
                entity_type,
                entity_id,
                actor,
                action,
                details_json,
                previous_hash,
                entry_hash,
            )

            logger.info(
                "audit.entry_appended",
                entry_id=row["id"],
                event_type=event_type,
                entity_id=entity_id,
                action=action,
            )

            return dict(row)
        finally:
            await conn.close()
    except Exception as e:
        logger.error("audit.append_failed", error=str(e))
        raise


async def verify_chain_integrity() -> dict:
    """
    Verify the integrity of the entire audit chain.

    Re-computes each entry's hash and checks it matches the stored hash.
    Also verifies that each entry's previous_hash matches the preceding entry.
    """
    try:
        import asyncpg

        db_url = os.getenv("DATABASE_URL", "postgresql://ide_agent:localdev@localhost:5432/onestream_ide")
        conn = await asyncpg.connect(dsn=db_url)
        try:
            rows = await conn.fetch(
                """SELECT id, event_type, entity_type, entity_id, actor, action,
                          details, previous_hash, entry_hash
                   FROM audit_log ORDER BY id ASC"""
            )

            if not rows:
                return {"valid": True, "entries_checked": 0}

            valid = True
            broken_at: int | None = None
            prev_hash: str | None = None

            for row in rows:
                # Verify chain link
                if row["previous_hash"] != prev_hash:
                    valid = False
                    broken_at = row["id"]
                    break

                # Verify entry hash
                details_json = json.dumps(json.loads(row["details"]) if row["details"] else {}, sort_keys=True)
                expected_input = (
                    f"{row['previous_hash'] or ''}|{row['event_type']}|{row['entity_type']}|"
                    f"{row['entity_id']}|{row['actor']}|{row['action']}|{details_json}"
                )
                expected_hash = hashlib.sha256(expected_input.encode("utf-8")).hexdigest()

                if expected_hash != row["entry_hash"]:
                    valid = False
                    broken_at = row["id"]
                    break

                prev_hash = row["entry_hash"]

            return {
                "valid": valid,
                "entries_checked": len(rows),
                "broken_at": broken_at,
            }
        finally:
            await conn.close()
    except Exception as e:
        logger.error("audit.verify_failed", error=str(e))
        return {"valid": False, "error": str(e)}
