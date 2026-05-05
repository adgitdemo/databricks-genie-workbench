"""Cycle 10 W4.3 — patch-type-aware narrow-L6 replacement."""
from __future__ import annotations


def test_filter_returns_narrowed_predicate(monkeypatch):
    monkeypatch.setenv("GSO_L6_NARROW_REPLACEMENT_PATCH_AWARE", "1")
    from genie_space_optimizer.optimization.cluster_driven_synthesis import (
        build_narrow_l6_replacement,
    )
    parent = {
        "patch_type": "add_sql_snippet_filter",
        "where_predicate": "outbound_total = 1",
        "qid_predicate_column": "query_id",
        "proposal_id": "P002",
    }
    out = build_narrow_l6_replacement(
        original_patch=parent,
        ag_target_qids=("gs_009",),
        root_cause="missing_filter",
    )
    assert out is not None
    assert "query_id IN ('gs_009')" in out["where_predicate"]


def test_measure_returns_none_with_reason(monkeypatch):
    monkeypatch.setenv("GSO_L6_NARROW_REPLACEMENT_PATCH_AWARE", "1")
    from genie_space_optimizer.optimization.cluster_driven_synthesis import (
        build_narrow_l6_replacement,
        narrow_replacement_diagnosis,
    )
    parent = {
        "patch_type": "add_sql_snippet_measure",
        "proposal_id": "P002",
    }
    out = build_narrow_l6_replacement(
        original_patch=parent,
        ag_target_qids=("gs_009",),
        root_cause="missing_filter",
    )
    assert out is None
    diag = narrow_replacement_diagnosis(
        original_patch=parent,
        ag_target_qids=("gs_009",),
        root_cause="missing_filter",
    )
    assert diag["applicable"] is False
    assert diag["reason"] == "patch_type_lacks_where_predicate"
    assert diag["original_patch_type"] == "add_sql_snippet_measure"


def test_expression_returns_none_with_reason(monkeypatch):
    monkeypatch.setenv("GSO_L6_NARROW_REPLACEMENT_PATCH_AWARE", "1")
    from genie_space_optimizer.optimization.cluster_driven_synthesis import (
        narrow_replacement_diagnosis,
    )
    parent = {
        "patch_type": "add_sql_snippet_expression",
        "proposal_id": "P003",
    }
    diag = narrow_replacement_diagnosis(
        original_patch=parent,
        ag_target_qids=("gs_009",),
        root_cause="missing_filter",
    )
    assert diag["applicable"] is False
    assert diag["reason"] == "patch_type_lacks_where_predicate"


def test_flag_off_byte_stable_with_filter(monkeypatch):
    monkeypatch.setenv("GSO_L6_NARROW_REPLACEMENT_PATCH_AWARE", "0")
    from genie_space_optimizer.optimization.cluster_driven_synthesis import (
        build_narrow_l6_replacement,
    )
    parent = {
        "patch_type": "add_sql_snippet_filter",
        "where_predicate": "outbound_total = 1",
        "qid_predicate_column": "query_id",
        "proposal_id": "P002",
    }
    out = build_narrow_l6_replacement(
        original_patch=parent,
        ag_target_qids=("gs_009",),
        root_cause="missing_filter",
    )
    assert out is not None
    assert "query_id IN ('gs_009')" in out["where_predicate"]
