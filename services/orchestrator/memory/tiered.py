"""Tiered memory system — session, project, team, global scopes."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import structlog

logger = structlog.get_logger()


class MemoryScope(str, Enum):
    SESSION = "session"    # Current conversation
    PROJECT = "project"    # Persists per project
    TEAM = "team"          # Shared across team members
    GLOBAL = "global"      # Platform-wide knowledge


@dataclass
class MemoryEntry:
    key: str
    value: str
    scope: MemoryScope
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0


class TieredMemory:
    """Multi-scope memory for agent context management.

    Resolution order: session → project → team → global.
    More specific scopes override broader ones.
    """

    def __init__(self) -> None:
        self._stores: dict[MemoryScope, dict[str, MemoryEntry]] = defaultdict(dict)

    def store(
        self,
        key: str,
        value: str,
        scope: MemoryScope = MemoryScope.SESSION,
        metadata: dict | None = None,
    ) -> None:
        """Store a memory entry at the specified scope."""
        entry = MemoryEntry(
            key=key,
            value=value,
            scope=scope,
            metadata=metadata or {},
        )
        self._stores[scope][key] = entry
        logger.debug("memory.stored", key=key, scope=scope.value)

    def retrieve(self, key: str, scope: MemoryScope | None = None) -> str | None:
        """Retrieve a memory entry.

        If scope is specified, only search that scope.
        Otherwise, search in resolution order: session → project → team → global.
        """
        if scope:
            entry = self._stores[scope].get(key)
            if entry:
                entry.access_count += 1
                return entry.value
            return None

        # Resolution order: most specific to least specific
        for s in [MemoryScope.SESSION, MemoryScope.PROJECT, MemoryScope.TEAM, MemoryScope.GLOBAL]:
            entry = self._stores[s].get(key)
            if entry:
                entry.access_count += 1
                return entry.value

        return None

    def list_entries(self, scope: MemoryScope | None = None) -> list[MemoryEntry]:
        """List all memory entries, optionally filtered by scope."""
        if scope:
            return list(self._stores[scope].values())
        entries = []
        for s in MemoryScope:
            entries.extend(self._stores[s].values())
        return entries

    def clear(self, scope: MemoryScope) -> int:
        """Clear all entries in a scope. Returns count of removed entries."""
        count = len(self._stores[scope])
        self._stores[scope].clear()
        logger.info("memory.cleared", scope=scope.value, count=count)
        return count

    def get_context_for_agent(self, project_id: str | None = None) -> dict[str, str]:
        """Build a context dict for agent consumption.

        Merges all scopes in resolution order (global overridden by more specific).
        """
        context: dict[str, str] = {}

        for s in [MemoryScope.GLOBAL, MemoryScope.TEAM, MemoryScope.PROJECT, MemoryScope.SESSION]:
            for key, entry in self._stores[s].items():
                context[key] = entry.value

        return context
