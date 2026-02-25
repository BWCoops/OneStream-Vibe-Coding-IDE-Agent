"""Tests for the DAG scheduler — validation, cycle detection, topological sort.

These are pure logic tests with no mocks needed.

Covers:
- Cycle detection in stage dependency graphs
- Missing dependency detection
- Invalid stage type detection
- Missing connector type detection
- Topological sort correctness
- Parallel layer detection (stages with no interdependencies in same layer)
- Edge cases: empty pipeline, single stage, diamond dependencies
"""

from __future__ import annotations

import pytest

from scheduler.dag import _has_cycle, topological_sort, validate_dag

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers — pipeline definition builders
# ---------------------------------------------------------------------------
def _stage(stage_id: str, stage_type: str = "EXTRACT", deps: list[str] | None = None, connector_type: str = "csv") -> dict:
    """Build a minimal stage dict."""
    return {
        "id": stage_id,
        "type": stage_type,
        "dependencies": deps or [],
        "connector": {"type": connector_type},
    }


def _pipeline(*stages: dict) -> dict:
    """Wrap stages into a pipeline definition."""
    return {"stages": list(stages)}


# ---------------------------------------------------------------------------
# validate_dag tests
# ---------------------------------------------------------------------------
class TestValidateDag:
    """Tests for the DAG validation function."""

    def test_valid_linear_pipeline(self):
        defn = _pipeline(
            _stage("s1", "EXTRACT"),
            _stage("s2", "TRANSFORM", deps=["s1"]),
            _stage("s3", "LOAD", deps=["s2"]),
        )
        issues = validate_dag(defn)
        assert issues == []

    def test_valid_parallel_pipeline(self):
        defn = _pipeline(
            _stage("ext_a", "EXTRACT"),
            _stage("ext_b", "EXTRACT"),
            _stage("merge", "TRANSFORM", deps=["ext_a", "ext_b"]),
            _stage("load", "LOAD", deps=["merge"]),
        )
        issues = validate_dag(defn)
        assert issues == []

    def test_empty_pipeline_reports_no_stages(self):
        defn = {"stages": []}
        issues = validate_dag(defn)
        assert len(issues) == 1
        assert "no stages" in issues[0].lower()

    def test_missing_stages_key(self):
        defn = {}
        issues = validate_dag(defn)
        assert len(issues) == 1
        assert "no stages" in issues[0].lower()

    def test_detects_missing_dependency(self):
        defn = _pipeline(
            _stage("s1", "EXTRACT"),
            _stage("s2", "TRANSFORM", deps=["nonexistent"]),
        )
        issues = validate_dag(defn)
        assert any("nonexistent" in i for i in issues)

    def test_detects_cycle(self):
        defn = _pipeline(
            _stage("a", "EXTRACT", deps=["c"]),
            _stage("b", "TRANSFORM", deps=["a"]),
            _stage("c", "LOAD", deps=["b"]),
        )
        issues = validate_dag(defn)
        assert any("cycle" in i.lower() for i in issues)

    def test_detects_self_cycle(self):
        defn = _pipeline(
            _stage("a", "EXTRACT", deps=["a"]),
        )
        issues = validate_dag(defn)
        assert any("cycle" in i.lower() for i in issues)

    def test_detects_invalid_stage_type(self):
        defn = _pipeline(
            _stage("s1", "INVALID_TYPE"),
        )
        issues = validate_dag(defn)
        assert any("invalid type" in i.lower() for i in issues)

    def test_valid_stage_types_accepted(self):
        for st in ("EXTRACT", "TRANSFORM", "VALIDATE", "LOAD"):
            defn = _pipeline(_stage("s1", st))
            issues = validate_dag(defn)
            type_issues = [i for i in issues if "invalid type" in i.lower()]
            assert type_issues == [], f"Type {st} should be valid"

    def test_detects_missing_connector_type(self):
        defn = _pipeline(
            {"id": "s1", "type": "EXTRACT", "dependencies": [], "connector": {}},
        )
        issues = validate_dag(defn)
        assert any("connector type" in i.lower() for i in issues)

    def test_detects_missing_connector_entirely(self):
        defn = _pipeline(
            {"id": "s1", "type": "EXTRACT", "dependencies": []},
        )
        issues = validate_dag(defn)
        assert any("connector type" in i.lower() for i in issues)

    def test_multiple_issues_reported(self):
        defn = _pipeline(
            _stage("s1", "INVALID"),
            _stage("s2", "TRANSFORM", deps=["missing_dep"]),
        )
        issues = validate_dag(defn)
        assert len(issues) >= 2  # At least type issue + missing dep


# ---------------------------------------------------------------------------
# _has_cycle tests
# ---------------------------------------------------------------------------
class TestHasCycle:
    """Tests for cycle detection in stage lists."""

    def test_no_cycle_in_linear_chain(self):
        stages = [
            _stage("a", deps=[]),
            _stage("b", deps=["a"]),
            _stage("c", deps=["b"]),
        ]
        assert _has_cycle(stages) is False

    def test_cycle_detected_simple(self):
        stages = [
            _stage("a", deps=["b"]),
            _stage("b", deps=["a"]),
        ]
        assert _has_cycle(stages) is True

    def test_cycle_detected_three_nodes(self):
        stages = [
            _stage("a", deps=["c"]),
            _stage("b", deps=["a"]),
            _stage("c", deps=["b"]),
        ]
        assert _has_cycle(stages) is True

    def test_self_loop(self):
        stages = [_stage("a", deps=["a"])]
        assert _has_cycle(stages) is True

    def test_no_cycle_diamond(self):
        stages = [
            _stage("a", deps=[]),
            _stage("b", deps=["a"]),
            _stage("c", deps=["a"]),
            _stage("d", deps=["b", "c"]),
        ]
        assert _has_cycle(stages) is False

    def test_single_node_no_deps(self):
        stages = [_stage("a", deps=[])]
        assert _has_cycle(stages) is False

    def test_disconnected_components_no_cycle(self):
        stages = [
            _stage("a", deps=[]),
            _stage("b", deps=[]),
            _stage("c", deps=[]),
        ]
        assert _has_cycle(stages) is False

    def test_ignores_unknown_dependencies(self):
        """Dependencies referencing non-existent stages are ignored in cycle detection."""
        stages = [
            _stage("a", deps=[]),
            _stage("b", deps=["a", "nonexistent"]),
        ]
        assert _has_cycle(stages) is False


# ---------------------------------------------------------------------------
# topological_sort tests
# ---------------------------------------------------------------------------
class TestTopologicalSort:
    """Tests for topological sort with parallel layer detection."""

    def test_linear_chain_produces_sequential_layers(self):
        stages = [
            _stage("a", deps=[]),
            _stage("b", deps=["a"]),
            _stage("c", deps=["b"]),
        ]
        layers = topological_sort(stages)

        assert len(layers) == 3
        assert layers[0] == ["a"]
        assert layers[1] == ["b"]
        assert layers[2] == ["c"]

    def test_parallel_roots_in_same_layer(self):
        stages = [
            _stage("a", deps=[]),
            _stage("b", deps=[]),
            _stage("c", deps=["a", "b"]),
        ]
        layers = topological_sort(stages)

        assert len(layers) == 2
        # First layer should contain both a and b (order within layer may vary)
        assert set(layers[0]) == {"a", "b"}
        assert layers[1] == ["c"]

    def test_diamond_dependency_produces_three_layers(self):
        stages = [
            _stage("a", deps=[]),
            _stage("b", deps=["a"]),
            _stage("c", deps=["a"]),
            _stage("d", deps=["b", "c"]),
        ]
        layers = topological_sort(stages)

        assert len(layers) == 3
        assert layers[0] == ["a"]
        assert set(layers[1]) == {"b", "c"}
        assert layers[2] == ["d"]

    def test_single_node(self):
        stages = [_stage("only")]
        layers = topological_sort(stages)

        assert len(layers) == 1
        assert layers[0] == ["only"]

    def test_all_independent_stages_single_layer(self):
        stages = [
            _stage("a", deps=[]),
            _stage("b", deps=[]),
            _stage("c", deps=[]),
            _stage("d", deps=[]),
        ]
        layers = topological_sort(stages)

        assert len(layers) == 1
        assert set(layers[0]) == {"a", "b", "c", "d"}

    def test_complex_dag_correct_layer_count(self):
        """
        a -> c -> e
        b -> d -> e
        a -> d
        """
        stages = [
            _stage("a", deps=[]),
            _stage("b", deps=[]),
            _stage("c", deps=["a"]),
            _stage("d", deps=["a", "b"]),
            _stage("e", deps=["c", "d"]),
        ]
        layers = topological_sort(stages)

        assert len(layers) == 3
        assert set(layers[0]) == {"a", "b"}
        assert set(layers[1]) == {"c", "d"}
        assert layers[2] == ["e"]

    def test_all_stages_appear_in_output(self):
        stages = [
            _stage("a", deps=[]),
            _stage("b", deps=["a"]),
            _stage("c", deps=["a"]),
            _stage("d", deps=["b", "c"]),
        ]
        layers = topological_sort(stages)

        all_ids = [sid for layer in layers for sid in layer]
        assert set(all_ids) == {"a", "b", "c", "d"}

    def test_empty_stages_returns_empty_layers(self):
        layers = topological_sort([])
        assert layers == []

    def test_wide_fan_out(self):
        """One source feeds many independent targets."""
        stages = [_stage("root", deps=[])]
        for i in range(10):
            stages.append(_stage(f"leaf_{i}", deps=["root"]))

        layers = topological_sort(stages)

        assert len(layers) == 2
        assert layers[0] == ["root"]
        assert len(layers[1]) == 10

    def test_wide_fan_in(self):
        """Many sources feed one target."""
        stages = []
        for i in range(5):
            stages.append(_stage(f"src_{i}", deps=[]))
        stages.append(_stage("sink", deps=[f"src_{i}" for i in range(5)]))

        layers = topological_sort(stages)

        assert len(layers) == 2
        assert set(layers[0]) == {f"src_{i}" for i in range(5)}
        assert layers[1] == ["sink"]
