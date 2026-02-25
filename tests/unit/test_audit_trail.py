"""Tests for the immutable audit trail with hash chaining.

Tests the hash chaining logic directly (pure logic), and tests the
async DB functions with mocked asyncpg.

Covers:
- Hash computation produces a valid SHA-256 hex string
- Hash includes previous entry hash for chaining
- Chain verification detects tampering
- Chain verification passes for valid chain
- Empty chain is considered valid
"""

from __future__ import annotations

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Pure-logic hash chaining tests (no DB needed)
# ---------------------------------------------------------------------------
def _compute_entry_hash(
    previous_hash: str | None,
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor: str,
    action: str,
    details: dict | None = None,
) -> str:
    """Replicate the hash computation from audit/trail.py."""
    details_json = json.dumps(details or {}, sort_keys=True)
    hash_input = (
        f"{previous_hash or ''}|{event_type}|{entity_type}|"
        f"{entity_id}|{actor}|{action}|{details_json}"
    )
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


def _build_chain(entries: list[dict]) -> list[dict]:
    """Build a valid chain of audit entries with correct hashes."""
    chain: list[dict] = []
    prev_hash: str | None = None

    for entry in entries:
        entry_hash = _compute_entry_hash(
            previous_hash=prev_hash,
            event_type=entry["event_type"],
            entity_type=entry["entity_type"],
            entity_id=entry["entity_id"],
            actor=entry["actor"],
            action=entry["action"],
            details=entry.get("details"),
        )
        chain.append(
            {
                "id": len(chain) + 1,
                "event_type": entry["event_type"],
                "entity_type": entry["entity_type"],
                "entity_id": entry["entity_id"],
                "actor": entry["actor"],
                "action": entry["action"],
                "details": json.dumps(entry.get("details") or {}, sort_keys=True),
                "previous_hash": prev_hash,
                "entry_hash": entry_hash,
            }
        )
        prev_hash = entry_hash

    return chain


def _verify_chain(rows: list[dict]) -> dict:
    """Pure-Python chain verification matching audit/trail.py logic."""
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
        details_json = json.dumps(
            json.loads(row["details"]) if row["details"] else {},
            sort_keys=True,
        )
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


class TestHashComputation:
    """Tests for the hash computation function."""

    def test_produces_sha256_hex(self):
        h = _compute_entry_hash(None, "code_gen", "rule", "rule-1", "alice", "create")
        assert len(h) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self):
        h1 = _compute_entry_hash(None, "code_gen", "rule", "rule-1", "alice", "create")
        h2 = _compute_entry_hash(None, "code_gen", "rule", "rule-1", "alice", "create")
        assert h1 == h2

    def test_different_inputs_produce_different_hashes(self):
        h1 = _compute_entry_hash(None, "code_gen", "rule", "rule-1", "alice", "create")
        h2 = _compute_entry_hash(None, "code_gen", "rule", "rule-1", "bob", "create")
        assert h1 != h2

    def test_previous_hash_affects_result(self):
        h1 = _compute_entry_hash(None, "code_gen", "rule", "rule-1", "alice", "create")
        h2 = _compute_entry_hash("abc123", "code_gen", "rule", "rule-1", "alice", "create")
        assert h1 != h2

    def test_details_included_in_hash(self):
        h1 = _compute_entry_hash(None, "code_gen", "rule", "rule-1", "alice", "create", {})
        h2 = _compute_entry_hash(None, "code_gen", "rule", "rule-1", "alice", "create", {"key": "value"})
        assert h1 != h2

    def test_details_sorted_keys_ensure_consistency(self):
        h1 = _compute_entry_hash(None, "e", "t", "id", "a", "act", {"b": 2, "a": 1})
        h2 = _compute_entry_hash(None, "e", "t", "id", "a", "act", {"a": 1, "b": 2})
        assert h1 == h2


class TestChainIntegrity:
    """Tests for hash chain verification."""

    def test_valid_chain_passes(self):
        entries = [
            {"event_type": "code_gen", "entity_type": "rule", "entity_id": "r1", "actor": "alice", "action": "create"},
            {"event_type": "review", "entity_type": "rule", "entity_id": "r1", "actor": "bob", "action": "approve"},
            {"event_type": "deploy", "entity_type": "rule", "entity_id": "r1", "actor": "charlie", "action": "deploy"},
        ]
        chain = _build_chain(entries)
        result = _verify_chain(chain)

        assert result["valid"] is True
        assert result["entries_checked"] == 3
        assert result.get("broken_at") is None

    def test_empty_chain_is_valid(self):
        result = _verify_chain([])
        assert result["valid"] is True
        assert result["entries_checked"] == 0

    def test_single_entry_chain_is_valid(self):
        entries = [
            {"event_type": "code_gen", "entity_type": "rule", "entity_id": "r1", "actor": "alice", "action": "create"},
        ]
        chain = _build_chain(entries)
        result = _verify_chain(chain)

        assert result["valid"] is True
        assert result["entries_checked"] == 1

    def test_tampered_entry_hash_detected(self):
        entries = [
            {"event_type": "code_gen", "entity_type": "rule", "entity_id": "r1", "actor": "alice", "action": "create"},
            {"event_type": "review", "entity_type": "rule", "entity_id": "r1", "actor": "bob", "action": "approve"},
        ]
        chain = _build_chain(entries)

        # Tamper with the second entry's hash
        chain[1]["entry_hash"] = "0" * 64
        result = _verify_chain(chain)

        assert result["valid"] is False
        assert result["broken_at"] == 2

    def test_tampered_previous_hash_detected(self):
        entries = [
            {"event_type": "code_gen", "entity_type": "rule", "entity_id": "r1", "actor": "alice", "action": "create"},
            {"event_type": "review", "entity_type": "rule", "entity_id": "r1", "actor": "bob", "action": "approve"},
        ]
        chain = _build_chain(entries)

        # Tamper with the second entry's previous_hash
        chain[1]["previous_hash"] = "tampered"
        result = _verify_chain(chain)

        assert result["valid"] is False
        assert result["broken_at"] == 2

    def test_tampered_data_field_detected(self):
        entries = [
            {"event_type": "code_gen", "entity_type": "rule", "entity_id": "r1", "actor": "alice", "action": "create"},
            {"event_type": "review", "entity_type": "rule", "entity_id": "r1", "actor": "bob", "action": "approve"},
        ]
        chain = _build_chain(entries)

        # Tamper with a data field (change the actor)
        chain[1]["actor"] = "mallory"
        result = _verify_chain(chain)

        assert result["valid"] is False
        assert result["broken_at"] == 2

    def test_removed_entry_breaks_chain(self):
        entries = [
            {"event_type": "code_gen", "entity_type": "rule", "entity_id": "r1", "actor": "alice", "action": "create"},
            {"event_type": "review", "entity_type": "rule", "entity_id": "r1", "actor": "bob", "action": "approve"},
            {"event_type": "deploy", "entity_type": "rule", "entity_id": "r1", "actor": "charlie", "action": "deploy"},
        ]
        chain = _build_chain(entries)

        # Remove the middle entry
        tampered_chain = [chain[0], chain[2]]
        result = _verify_chain(tampered_chain)

        assert result["valid"] is False
        assert result["broken_at"] == 3

    def test_first_entry_must_have_no_previous_hash(self):
        entries = [
            {"event_type": "code_gen", "entity_type": "rule", "entity_id": "r1", "actor": "alice", "action": "create"},
        ]
        chain = _build_chain(entries)

        # Tamper: set previous_hash on the first entry
        chain[0]["previous_hash"] = "fake_hash"
        result = _verify_chain(chain)

        assert result["valid"] is False
        assert result["broken_at"] == 1

    def test_chain_with_details(self):
        entries = [
            {
                "event_type": "code_gen",
                "entity_type": "rule",
                "entity_id": "r1",
                "actor": "alice",
                "action": "create",
                "details": {"language": "vb.net", "lines": 42},
            },
            {
                "event_type": "review",
                "entity_type": "rule",
                "entity_id": "r1",
                "actor": "bob",
                "action": "approve",
                "details": {"score": 0.95},
            },
        ]
        chain = _build_chain(entries)
        result = _verify_chain(chain)

        assert result["valid"] is True

    def test_long_chain_integrity(self):
        """Verify a chain of 100 entries remains valid."""
        entries = [
            {
                "event_type": f"event_{i}",
                "entity_type": "rule",
                "entity_id": f"r-{i}",
                "actor": f"user_{i % 5}",
                "action": "update",
                "details": {"step": i},
            }
            for i in range(100)
        ]
        chain = _build_chain(entries)
        result = _verify_chain(chain)

        assert result["valid"] is True
        assert result["entries_checked"] == 100


# ---------------------------------------------------------------------------
# Async function tests (mocked DB)
# ---------------------------------------------------------------------------
class TestAppendAuditEntry:
    """Tests for the async append_audit_entry function with mocked DB."""

    @pytest.mark.asyncio
    async def test_append_computes_hash_and_stores(self, mock_db_conn):
        """Verify that append_audit_entry calls the DB with a computed hash."""
        mock_db_conn.fetchrow.side_effect = [
            # First call: get last entry (empty chain)
            None,
            # Second call: INSERT RETURNING
            {
                "id": 1,
                "event_type": "code_gen",
                "entity_id": "r1",
                "actor": "alice",
                "action": "create",
                "entry_hash": "somehash",
                "created_at": "2026-01-01T00:00:00",
            },
        ]

        with patch("audit.trail.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(return_value=mock_db_conn)

            from audit.trail import append_audit_entry

            result = await append_audit_entry(
                event_type="code_gen",
                entity_type="rule",
                entity_id="r1",
                actor="alice",
                action="create",
                details={"language": "vb.net"},
            )

            assert result["event_type"] == "code_gen"
            assert mock_db_conn.fetchrow.call_count == 2


class TestVerifyChainIntegrity:
    """Tests for the async verify_chain_integrity function with mocked DB."""

    @pytest.mark.asyncio
    async def test_empty_db_returns_valid(self, mock_db_conn):
        mock_db_conn.fetch.return_value = []

        with patch("audit.trail.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(return_value=mock_db_conn)

            from audit.trail import verify_chain_integrity

            result = await verify_chain_integrity()

            assert result["valid"] is True
            assert result["entries_checked"] == 0
