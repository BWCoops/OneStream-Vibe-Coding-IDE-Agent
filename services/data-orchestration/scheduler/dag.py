"""DAG validation and topological sort for pipeline stages."""

from __future__ import annotations

from collections import deque

import structlog

logger = structlog.get_logger()


def validate_dag(definition: dict) -> list[str]:
    """Validate pipeline definition: check DAG structure, cycles, missing deps."""
    issues: list[str] = []
    stages = definition.get("stages", [])

    if not stages:
        issues.append("Pipeline has no stages defined")
        return issues

    stage_ids = {s["id"] for s in stages}

    # Check for missing dependencies
    for stage in stages:
        for dep_id in stage.get("dependencies", []):
            if dep_id not in stage_ids:
                issues.append(f"Stage '{stage['id']}' depends on unknown stage '{dep_id}'")

    # Check for cycles
    if _has_cycle(stages):
        issues.append("Pipeline DAG contains a cycle")

    # Check for valid stage types
    valid_types = {"EXTRACT", "TRANSFORM", "VALIDATE", "LOAD"}
    for stage in stages:
        if stage.get("type") not in valid_types:
            issues.append(f"Stage '{stage['id']}' has invalid type '{stage.get('type')}'")

    # Check for connector configuration
    for stage in stages:
        connector = stage.get("connector", {})
        if not connector.get("type"):
            issues.append(f"Stage '{stage['id']}' missing connector type")

    return issues


def topological_sort(stages: list[dict]) -> list[list[str]]:
    """
    Topological sort with parallelism detection.
    Returns a list of layers — stages in the same layer can run in parallel.
    """
    adj: dict[str, list[str]] = {s["id"]: [] for s in stages}
    in_degree: dict[str, int] = {s["id"]: 0 for s in stages}

    for stage in stages:
        for dep_id in stage.get("dependencies", []):
            adj[dep_id].append(stage["id"])
            in_degree[stage["id"]] += 1

    # BFS-based topological sort with level tracking
    queue = deque([sid for sid, deg in in_degree.items() if deg == 0])
    layers: list[list[str]] = []

    while queue:
        layer = list(queue)
        layers.append(layer)
        next_queue: deque[str] = deque()

        for sid in layer:
            for neighbor in adj[sid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_queue.append(neighbor)

        queue = next_queue

    return layers


def _has_cycle(stages: list[dict]) -> bool:
    """Detect cycles in the stage dependency graph."""
    stage_ids = {s["id"] for s in stages}
    adj: dict[str, list[str]] = {s["id"]: [] for s in stages}
    in_degree: dict[str, int] = {s["id"]: 0 for s in stages}

    for stage in stages:
        for dep_id in stage.get("dependencies", []):
            if dep_id in stage_ids:
                adj[dep_id].append(stage["id"])
                in_degree[stage["id"]] += 1

    queue = deque([sid for sid, deg in in_degree.items() if deg == 0])
    visited = 0

    while queue:
        sid = queue.popleft()
        visited += 1
        for neighbor in adj[sid]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return visited != len(stage_ids)
