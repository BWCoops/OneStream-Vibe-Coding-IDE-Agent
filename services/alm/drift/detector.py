"""Drift detection — compares deployed artefacts against source of truth."""

from __future__ import annotations

import hashlib
import os

import structlog

logger = structlog.get_logger()


async def detect_drift(environment_id: str, artefact_ids: list[str]) -> list[dict]:
    """
    Compare artefact source in the database against what's deployed in the OneStream environment.

    Drift detection works by:
    1. Loading expected source code from PostgreSQL (source of truth)
    2. Fetching actual deployed code from the OneStream environment via MCP
    3. Comparing hashes to detect differences
    """
    logger.info("drift.detect", environment_id=environment_id, artefact_count=len(artefact_ids))

    differences: list[dict] = []

    try:
        import asyncpg

        db_url = os.getenv("DATABASE_URL", "postgresql://ide_agent:localdev@localhost:5432/onestream_ide")
        conn = await asyncpg.connect(dsn=db_url)
        try:
            # Load expected source from DB
            for artefact_id in artefact_ids:
                row = await conn.fetchrow(
                    "SELECT id, name, source_code, version FROM artefacts WHERE id = $1",
                    artefact_id,
                )
                if not row:
                    differences.append({
                        "artefact_id": artefact_id,
                        "type": "missing_in_db",
                        "message": "Artefact not found in database",
                    })
                    continue

                expected_hash = _hash_code(row["source_code"])

                # In production: fetch actual code from OneStream via MCP onestream-rules
                # For now, flag as "unchecked" since we can't connect to OneStream
                differences.append({
                    "artefact_id": artefact_id,
                    "name": row["name"],
                    "expected_hash": expected_hash,
                    "expected_version": row["version"],
                    "type": "unchecked",
                    "message": "Environment connectivity required for drift detection",
                })
        finally:
            await conn.close()
    except Exception as e:
        logger.error("drift_detection_failed", error=str(e))
        differences.append({
            "type": "error",
            "message": f"Drift detection failed: {e}",
        })

    return differences


def _hash_code(source_code: str) -> str:
    """Generate a consistent hash of source code for comparison."""
    # Normalize whitespace for consistent comparison
    normalized = "\n".join(line.rstrip() for line in source_code.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
