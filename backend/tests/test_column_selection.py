"""Tests for the optional column allowlist (backend/services/column_selection.py).

Covers allowlist filtering, the "*" wildcard, disabled flag, missing/invalid
config, and unlisted-table fallback. Pure logic — no Databricks access.
"""

import json

import pytest

from backend.services import column_selection as cs


@pytest.fixture(autouse=True)
def _clear_cache():
    """Reset the module cache before and after each test."""
    cs._reset_cache_for_tests()
    yield
    cs._reset_cache_for_tests()


def _write_config(tmp_path, data_sources: dict) -> str:
    path = tmp_path / "columns.json"
    path.write_text(json.dumps({"data_sources": data_sources}), encoding="utf-8")
    return str(path)


def _enable(monkeypatch, config_path: str):
    monkeypatch.setenv("COLUMN_SELECTION_ENABLED", "true")
    monkeypatch.setenv("COLUMN_SELECTION_CONFIG", config_path)


# ---------------------------------------------------------------------------
# allowed_columns
# ---------------------------------------------------------------------------

class TestAllowedColumns:
    def test_returns_allowlist_for_listed_table(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"main.sales.orders": ["order_id", "amount"]})
        _enable(monkeypatch, cfg)
        assert cs.allowed_columns("main.sales.orders") == {"order_id", "amount"}

    def test_case_insensitive_table_and_columns(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"Main.Sales.Orders": ["Order_ID", "Amount"]})
        _enable(monkeypatch, cfg)
        assert cs.allowed_columns("MAIN.SALES.ORDERS") == {"order_id", "amount"}

    def test_wildcard_means_unrestricted(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"main.sales.orders": ["*"]})
        _enable(monkeypatch, cfg)
        assert cs.allowed_columns("main.sales.orders") is None

    def test_empty_list_means_unrestricted(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"main.sales.orders": []})
        _enable(monkeypatch, cfg)
        assert cs.allowed_columns("main.sales.orders") is None

    def test_unlisted_table_is_unrestricted(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"main.sales.orders": ["order_id"]})
        _enable(monkeypatch, cfg)
        assert cs.allowed_columns("main.sales.customers") is None

    def test_metric_view_dimensions_and_measures(self, tmp_path, monkeypatch):
        # A metric view lists its dimension/measure names (UC reports them as columns).
        cfg = _write_config(tmp_path, {
            "main.sales.sales_metrics": ["region", "order_month", "total_revenue"],
        })
        _enable(monkeypatch, cfg)
        cols = [
            {"name": "region"}, {"name": "order_month"},
            {"name": "total_revenue"}, {"name": "avg_order_value"},
        ]
        result = cs.filter_columns("main.sales.sales_metrics", cols, name_key="name")
        assert [c["name"] for c in result] == ["region", "order_month", "total_revenue"]

    def test_disabled_flag_returns_none(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"main.sales.orders": ["order_id"]})
        monkeypatch.setenv("COLUMN_SELECTION_ENABLED", "false")
        monkeypatch.setenv("COLUMN_SELECTION_CONFIG", cfg)
        assert cs.allowed_columns("main.sales.orders") is None

    def test_missing_config_file_returns_none(self, tmp_path, monkeypatch):
        _enable(monkeypatch, str(tmp_path / "does_not_exist.json"))
        assert cs.allowed_columns("main.sales.orders") is None

    def test_invalid_json_returns_none(self, tmp_path, monkeypatch):
        path = tmp_path / "bad.json"
        path.write_text("{ not valid json", encoding="utf-8")
        _enable(monkeypatch, str(path))
        assert cs.allowed_columns("main.sales.orders") is None

    def test_missing_data_sources_key_returns_none(self, tmp_path, monkeypatch):
        path = tmp_path / "cfg.json"
        path.write_text(json.dumps({"other": {}}), encoding="utf-8")
        _enable(monkeypatch, str(path))
        assert cs.allowed_columns("main.sales.orders") is None

    def test_enabled_without_config_path_returns_none(self, monkeypatch):
        monkeypatch.setenv("COLUMN_SELECTION_ENABLED", "true")
        monkeypatch.delenv("COLUMN_SELECTION_CONFIG", raising=False)
        assert cs.allowed_columns("main.sales.orders") is None


# ---------------------------------------------------------------------------
# filter_columns / filter_column_names
# ---------------------------------------------------------------------------

class TestFilterColumns:
    def test_filters_dicts_by_name_key(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"main.sales.orders": ["order_id", "amount"]})
        _enable(monkeypatch, cfg)
        cols = [{"name": "order_id"}, {"name": "amount"}, {"name": "secret_col"}]
        result = cs.filter_columns("main.sales.orders", cols, name_key="name")
        assert [c["name"] for c in result] == ["order_id", "amount"]

    def test_preserves_source_order(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"main.sales.orders": ["amount", "order_id"]})
        _enable(monkeypatch, cfg)
        cols = [{"name": "order_id"}, {"name": "amount"}]
        result = cs.filter_columns("main.sales.orders", cols, name_key="name")
        assert [c["name"] for c in result] == ["order_id", "amount"]

    def test_supports_column_name_key(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"main.sales.orders": ["order_id"]})
        _enable(monkeypatch, cfg)
        cols = [{"column_name": "order_id"}, {"column_name": "drop_me"}]
        result = cs.filter_columns("main.sales.orders", cols, name_key="column_name")
        assert [c["column_name"] for c in result] == ["order_id"]

    def test_unrestricted_returns_input_unchanged(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"main.sales.orders": ["*"]})
        _enable(monkeypatch, cfg)
        cols = [{"name": "a"}, {"name": "b"}]
        assert cs.filter_columns("main.sales.orders", cols) is cols

    def test_filter_column_names(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"main.sales.orders": ["order_id", "amount"]})
        _enable(monkeypatch, cfg)
        names = ["order_id", "AMOUNT", "leaked"]
        assert cs.filter_column_names("main.sales.orders", names) == ["order_id", "AMOUNT"]

    def test_filter_column_names_unrestricted(self, monkeypatch):
        monkeypatch.setenv("COLUMN_SELECTION_ENABLED", "false")
        names = ["a", "b"]
        assert cs.filter_column_names("main.sales.orders", names) == names


# ---------------------------------------------------------------------------
# parse_allowlist
# ---------------------------------------------------------------------------

class TestParseAllowlist:
    def test_basic(self):
        out = cs.parse_allowlist({"Main.Sales.Orders": ["Order_ID", "Amount"]})
        assert out == {"main.sales.orders": {"order_id", "amount"}}

    def test_wildcard_and_empty_are_unrestricted(self):
        out = cs.parse_allowlist({"a.b.c": ["*"], "d.e.f": []})
        assert out == {"a.b.c": set(), "d.e.f": set()}

    def test_non_dict_returns_empty(self):
        assert cs.parse_allowlist(["not", "a", "dict"]) == {}


# ---------------------------------------------------------------------------
# Per-space override precedence (no env/file needed)
# ---------------------------------------------------------------------------

class TestOverride:
    def test_override_used_without_global_config(self):
        # Feature disabled globally, but a per-space override still restricts.
        override = cs.parse_allowlist({"main.sales.orders": ["order_id"]})
        assert cs.allowed_columns("main.sales.orders", override=override) == {"order_id"}

    def test_override_beats_global_file(self, tmp_path, monkeypatch):
        cfg = _write_config(tmp_path, {"main.sales.orders": ["global_col"]})
        _enable(monkeypatch, cfg)
        override = cs.parse_allowlist({"main.sales.orders": ["per_space_col"]})
        # Override wins over the global file entry.
        assert cs.allowed_columns("main.sales.orders", override=override) == {"per_space_col"}

    def test_override_wildcard_is_unrestricted(self):
        override = cs.parse_allowlist({"main.sales.orders": ["*"]})
        assert cs.allowed_columns("main.sales.orders", override=override) is None

    def test_override_unlisted_table_unrestricted(self):
        override = cs.parse_allowlist({"main.sales.orders": ["order_id"]})
        assert cs.allowed_columns("main.sales.customers", override=override) is None

    def test_filter_columns_with_override(self):
        override = cs.parse_allowlist({"main.sales.orders": ["order_id", "amount"]})
        cols = [{"name": "order_id"}, {"name": "amount"}, {"name": "secret"}]
        out = cs.filter_columns("main.sales.orders", cols, name_key="name", override=override)
        assert [c["name"] for c in out] == ["order_id", "amount"]

    def test_filter_column_names_with_override(self):
        override = cs.parse_allowlist({"main.sales.orders": ["order_id"]})
        out = cs.filter_column_names("main.sales.orders", ["order_id", "nope"], override=override)
        assert out == ["order_id"]

    def test_empty_override_dict_is_unrestricted(self):
        # An empty parsed override ({}) means "no per-space config" → fall through to None.
        assert cs.allowed_columns("main.sales.orders", override={}) is None
