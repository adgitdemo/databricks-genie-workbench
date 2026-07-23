"""Tests for usage-history column recommendation (backend/services/column_usage.py).

Mocks the SP statement runner (system_tables._run) so no Databricks access is
needed. Covers base-table resolution (view/metric-view → sources), usage
aggregation + union, empty-history → empty list, and space→workspace fallback.
"""
from __future__ import annotations

import pytest

from backend.services import column_usage as cu


@pytest.fixture(autouse=True)
def _reset_health(monkeypatch):
    # Force system_tables_status to "available" unless a test overrides it.
    monkeypatch.setattr(cu._st, "system_tables_status", lambda: True)
    yield


def _install_runner(monkeypatch, handler):
    """Route both SQL paths through a single handler(sql) -> list[dict].

    - ``system_tables._run`` (SP path) is used for the column_lineage query.
    - ``execute_sql`` (OBO path) is used for information_schema view resolution;
      it returns the ``{columns, data, error}`` shape, so we adapt the handler's
      list-of-dicts output into that shape.
    """
    def fake_run(sql, params, *args, **kwargs):
        return handler(sql)
    monkeypatch.setattr(cu._st, "_run", fake_run)

    def fake_execute_sql(sql, *args, **kwargs):
        rows = handler(sql)
        if not rows:
            return {"columns": [], "data": [], "error": None}
        col_names = list(rows[0].keys())
        return {
            "columns": [{"name": c} for c in col_names],
            "data": [[r.get(c) for c in col_names] for r in rows],
            "error": None,
        }
    monkeypatch.setattr(cu, "execute_sql", fake_execute_sql)


# ---------------------------------------------------------------------------
# Table: own usage only
# ---------------------------------------------------------------------------

class TestTable:
    def test_table_uses_own_column_history(self, monkeypatch):
        def handler(sql: str):
            s = sql.lower()
            if "column_lineage" in s:
                return [
                    {"fqn": "main.sales.orders", "col": "order_id", "uses": 5},
                    {"fqn": "main.sales.orders", "col": "amount", "uses": 3},
                ]
            return []  # no view_table_usage / views rows for a real table
        _install_runner(monkeypatch, handler)

        out = cu.recommend_columns(
            "space1", [{"identifier": "main.sales.orders", "kind": "table"}]
        )
        assert out["data_sources"]["main.sales.orders"] == ["amount", "order_id"]
        assert out["meta"]["main.sales.orders"]["has_history"] is True
        assert out["meta"]["main.sales.orders"]["via_base_tables"] is False

    def test_table_no_history_excluded(self, monkeypatch):
        _install_runner(monkeypatch, lambda sql: [])
        out = cu.recommend_columns(
            "space1", [{"identifier": "main.sales.orders", "kind": "table"}]
        )
        assert "main.sales.orders" not in out["data_sources"]
        assert out["meta"]["main.sales.orders"]["has_history"] is False


# ---------------------------------------------------------------------------
# View: own usage + base-table usage (union)
# ---------------------------------------------------------------------------

class TestView:
    def test_view_unions_base_table_columns(self, monkeypatch):
        def handler(sql: str):
            s = sql.lower()
            if "view_table_usage" in s and "sales_v" in s:
                return [{
                    "table_catalog": "main", "table_schema": "sales",
                    "table_name": "orders",
                }]
            if "view_table_usage" in s:  # base table has no further bases
                return []
            if "column_lineage" in s:
                # View exposes region; base table contributes amount.
                return [
                    {"fqn": "main.sales.sales_v", "col": "region", "uses": 4},
                    {"fqn": "main.sales.orders", "col": "amount", "uses": 9},
                ]
            return []
        _install_runner(monkeypatch, handler)

        out = cu.recommend_columns(
            "space1", [{"identifier": "main.sales.sales_v", "kind": "view"}]
        )
        assert out["data_sources"]["main.sales.sales_v"] == ["amount", "region"]
        meta = out["meta"]["main.sales.sales_v"]
        assert meta["via_base_tables"] is True
        assert "main.sales.orders" in meta["analyzed_fqns"]

    def test_view_regex_fallback_when_usage_view_missing(self, monkeypatch):
        def handler(sql: str):
            s = sql.lower()
            if "view_table_usage" in s:
                return []  # unavailable → triggers regex fallback
            if "information_schema.views" in s:
                return [{"view_definition": "SELECT x FROM main.sales.orders o"}]
            if "column_lineage" in s:
                return [{"fqn": "main.sales.orders", "col": "x", "uses": 2}]
            return []
        _install_runner(monkeypatch, handler)

        out = cu.recommend_columns(
            "space1", [{"identifier": "main.sales.sales_v", "kind": "view"}]
        )
        assert out["data_sources"]["main.sales.sales_v"] == ["x"]
        assert out["meta"]["main.sales.sales_v"]["via_base_tables"] is True


# ---------------------------------------------------------------------------
# Metric view: YAML source base table
# ---------------------------------------------------------------------------

class TestMetricView:
    def test_metric_view_resolves_yaml_source(self, monkeypatch):
        def handler(sql: str):
            s = sql.lower()
            if "view_table_usage" in s:
                return []  # MV not in view_table_usage → regex/YAML path
            if "information_schema.views" in s:
                return [{"view_definition": "source: main.sales.orders\ndimensions:\n  - name: region"}]
            if "column_lineage" in s:
                return [
                    {"fqn": "main.sales.orders", "col": "region", "uses": 7},
                    {"fqn": "main.sales.metrics", "col": "total", "uses": 1},
                ]
            return []
        _install_runner(monkeypatch, handler)

        out = cu.recommend_columns(
            "space1", [{"identifier": "main.sales.metrics", "kind": "metric_view"}]
        )
        cols = out["data_sources"]["main.sales.metrics"]
        assert cols == ["region", "total"]
        assert out["meta"]["main.sales.metrics"]["via_base_tables"] is True


# ---------------------------------------------------------------------------
# Space → workspace-wide fallback
# ---------------------------------------------------------------------------

class TestFallback:
    def test_workspace_fallback_when_space_has_no_history(self, monkeypatch):
        calls = {"scoped": 0, "wide": 0}

        def handler(sql: str):
            s = sql.lower()
            if "column_lineage" in s:
                if "genie_space_id" in s:
                    calls["scoped"] += 1
                    return []  # space itself has nothing
                calls["wide"] += 1
                return [{"fqn": "main.sales.orders", "col": "amount", "uses": 12}]
            return []
        _install_runner(monkeypatch, handler)

        out = cu.recommend_columns(
            "space1", [{"identifier": "main.sales.orders", "kind": "table"}]
        )
        assert out["data_sources"]["main.sales.orders"] == ["amount"]
        assert calls["scoped"] == 1 and calls["wide"] == 1


# ---------------------------------------------------------------------------
# system_tables unavailable
# ---------------------------------------------------------------------------

class TestUnavailable:
    def test_reports_unavailable(self, monkeypatch):
        monkeypatch.setattr(cu._st, "system_tables_status", lambda: False)
        _install_runner(monkeypatch, lambda sql: [])
        out = cu.recommend_columns(
            "space1", [{"identifier": "main.sales.orders", "kind": "table"}]
        )
        assert out["system_tables_available"] is False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_parts_and_norm(self):
        assert cu._parts("Main.Sales.Orders") == ("main", "sales", "orders")
        assert cu._parts("bad.identifier") is None
        # _norm lowercases + trims surrounding whitespace/backticks; _parts strips
        # the per-segment backticks so a fully-backticked FQN still resolves.
        assert cu._norm("  MAIN.Sales.Orders ") == "main.sales.orders"
        assert cu._parts("`Main`.`Sales`.`Orders`") == ("main", "sales", "orders")

    def test_invalid_identifier_skipped(self, monkeypatch):
        _install_runner(monkeypatch, lambda sql: [])
        out = cu.recommend_columns("space1", [{"identifier": "not_qualified", "kind": "table"}])
        assert out["data_sources"] == {}
        assert out["meta"] == {}
