"""Tests for the column-level lineage tracker.

Pure logic tests — no mocks needed.

Covers:
- LineageGraph construction and add_mapping
- get_upstream / get_downstream queries
- to_dict serialization
- SQL lineage extraction (extract_lineage_from_sql)
  - Simple SELECT ... FROM
  - Column aliases (AS)
  - Table-qualified columns (t.column)
  - Expression columns (function calls)
"""

from __future__ import annotations

import pytest

from lineage.tracker import (
    ColumnLineage,
    LineageGraph,
    extract_lineage_from_sql,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# LineageGraph tests
# ---------------------------------------------------------------------------
class TestLineageGraph:
    """Tests for the LineageGraph dataclass methods."""

    def _make_graph(self) -> LineageGraph:
        g = LineageGraph(pipeline_id="pipe-001", execution_id="exec-001")
        g.add_mapping("extract", "amount", "transform", "amount_usd", "amount * fx_rate")
        g.add_mapping("extract", "entity", "transform", "entity")
        g.add_mapping("transform", "amount_usd", "load", "Amount")
        g.add_mapping("transform", "entity", "load", "Entity")
        return g

    def test_add_mapping_increases_count(self):
        g = LineageGraph(pipeline_id="p", execution_id="e")
        assert len(g.mappings) == 0

        g.add_mapping("src", "col_a", "tgt", "col_b")
        assert len(g.mappings) == 1

    def test_add_mapping_creates_column_lineage(self):
        g = LineageGraph(pipeline_id="p", execution_id="e")
        g.add_mapping("src", "col_a", "tgt", "col_b", "UPPER(col_a)")

        m = g.mappings[0]
        assert isinstance(m, ColumnLineage)
        assert m.source_stage == "src"
        assert m.source_column == "col_a"
        assert m.target_stage == "tgt"
        assert m.target_column == "col_b"
        assert m.transformation == "UPPER(col_a)"

    def test_get_upstream_returns_correct_mappings(self):
        g = self._make_graph()
        upstream = g.get_upstream("load", "Amount")

        assert len(upstream) == 1
        assert upstream[0].source_stage == "transform"
        assert upstream[0].source_column == "amount_usd"

    def test_get_upstream_returns_empty_for_root(self):
        g = self._make_graph()
        upstream = g.get_upstream("extract", "amount")
        assert upstream == []

    def test_get_downstream_returns_correct_mappings(self):
        g = self._make_graph()
        downstream = g.get_downstream("extract", "amount")

        assert len(downstream) == 1
        assert downstream[0].target_stage == "transform"
        assert downstream[0].target_column == "amount_usd"

    def test_get_downstream_returns_empty_for_leaf(self):
        g = self._make_graph()
        downstream = g.get_downstream("load", "Amount")
        assert downstream == []

    def test_get_upstream_nonexistent_column(self):
        g = self._make_graph()
        result = g.get_upstream("transform", "nonexistent")
        assert result == []

    def test_get_downstream_nonexistent_stage(self):
        g = self._make_graph()
        result = g.get_downstream("nonexistent", "col")
        assert result == []

    def test_multiple_upstream_sources(self):
        g = LineageGraph(pipeline_id="p", execution_id="e")
        g.add_mapping("src_a", "val", "merge", "total")
        g.add_mapping("src_b", "val", "merge", "total")

        upstream = g.get_upstream("merge", "total")
        assert len(upstream) == 2
        sources = {m.source_stage for m in upstream}
        assert sources == {"src_a", "src_b"}

    def test_multiple_downstream_targets(self):
        g = LineageGraph(pipeline_id="p", execution_id="e")
        g.add_mapping("extract", "amount", "target_a", "amount")
        g.add_mapping("extract", "amount", "target_b", "amount_copy")

        downstream = g.get_downstream("extract", "amount")
        assert len(downstream) == 2

    def test_to_dict_structure(self):
        g = LineageGraph(pipeline_id="pipe-001", execution_id="exec-001")
        g.add_mapping("src", "col_a", "tgt", "col_b", "SUM(col_a)")

        d = g.to_dict()
        assert d["pipeline_id"] == "pipe-001"
        assert d["execution_id"] == "exec-001"
        assert len(d["mappings"]) == 1

        m = d["mappings"][0]
        assert m["source_stage"] == "src"
        assert m["source_column"] == "col_a"
        assert m["target_stage"] == "tgt"
        assert m["target_column"] == "col_b"
        assert m["transformation"] == "SUM(col_a)"

    def test_to_dict_empty_graph(self):
        g = LineageGraph(pipeline_id="p", execution_id="e")
        d = g.to_dict()
        assert d["mappings"] == []


# ---------------------------------------------------------------------------
# extract_lineage_from_sql tests
# ---------------------------------------------------------------------------
class TestExtractLineageFromSql:
    """Tests for SQL-based lineage extraction."""

    def test_simple_select(self):
        sql = "SELECT amount, entity FROM staging"
        lineage = extract_lineage_from_sql(sql, "staging", "target")

        assert len(lineage) == 2
        cols = {(m.source_column, m.target_column) for m in lineage}
        assert ("amount", "amount") in cols
        assert ("entity", "entity") in cols

    def test_column_alias(self):
        sql = "SELECT amount AS amount_usd FROM staging"
        lineage = extract_lineage_from_sql(sql, "src", "tgt")

        assert len(lineage) == 1
        m = lineage[0]
        assert m.source_column == "amount"
        assert m.target_column == "amount_usd"
        assert m.transformation != ""  # Should record the alias expression

    def test_table_qualified_columns(self):
        sql = "SELECT t.amount, t.entity FROM staging"
        lineage = extract_lineage_from_sql(sql, "src", "tgt")

        assert len(lineage) == 2
        # Table alias prefix should be stripped
        cols = {m.source_column for m in lineage}
        assert "amount" in cols
        assert "entity" in cols

    def test_expression_column(self):
        sql = "SELECT SUM(amount) AS total FROM staging"
        lineage = extract_lineage_from_sql(sql, "src", "tgt")

        assert len(lineage) == 1
        m = lineage[0]
        assert m.target_column == "total"
        assert m.transformation != ""  # Should note the expression

    def test_mixed_columns_and_expressions(self):
        sql = "SELECT entity, SUM(amount) AS total, period FROM staging"
        lineage = extract_lineage_from_sql(sql, "src", "tgt")

        assert len(lineage) == 3

    def test_non_select_sql_returns_empty(self):
        sql = "INSERT INTO target (col) VALUES (1)"
        lineage = extract_lineage_from_sql(sql, "src", "tgt")
        assert lineage == []

    def test_empty_sql_returns_empty(self):
        lineage = extract_lineage_from_sql("", "src", "tgt")
        assert lineage == []

    def test_case_insensitive_select(self):
        sql = "select amount, entity from staging"
        lineage = extract_lineage_from_sql(sql, "src", "tgt")
        assert len(lineage) == 2

    def test_source_and_target_stages_set_correctly(self):
        sql = "SELECT col FROM staging"
        lineage = extract_lineage_from_sql(sql, "my_source", "my_target")

        assert all(m.source_stage == "my_source" for m in lineage)
        assert all(m.target_stage == "my_target" for m in lineage)

    def test_multiple_table_aliases(self):
        sql = "SELECT a.id, b.name FROM table_a a JOIN table_b b"
        lineage = extract_lineage_from_sql(sql, "src", "tgt")

        assert len(lineage) == 2
        cols = {m.source_column for m in lineage}
        assert "id" in cols
        assert "name" in cols
