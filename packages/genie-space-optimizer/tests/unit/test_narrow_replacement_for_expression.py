"""P0 Task 2A: contract for expression / measure narrow replacement."""

from __future__ import annotations

import pytest


def _h002_expression_patch() -> dict:
    return {
        "proposal_id": "L6:P001#3",
        "patch_type": "add_sql_snippet_expression",
        "target": "mv_esr_dim_location.zone_vp_name",
        "sql_expression": (
            "CASE WHEN role = 'VP' AND zone IS NOT NULL THEN name END"
        ),
        "rationale": "plural top-N collapse for zone-VP",
    }


def _h002_measure_patch() -> dict:
    return {
        "proposal_id": "L6:P002#1",
        "patch_type": "add_sql_snippet_measure",
        "target": "mv_esr_fct_orders.zone_vp_total_orders",
        "sql_expression": (
            "SUM(CASE WHEN role = 'VP' THEN order_count END)"
        ),
        "rationale": "VP order rollup",
    }


def test_diagnose_expression_patch_is_now_applicable_when_flag_on(
    monkeypatch,
) -> None:
    monkeypatch.setenv("GSO_L6_NARROW_REPLACEMENT_FOR_EXPRESSION", "1")
    from genie_space_optimizer.optimization.cluster_driven_synthesis import (
        narrow_replacement_diagnosis,
    )

    diag = narrow_replacement_diagnosis(
        original_patch=_h002_expression_patch(),
        ag_target_qids=("7now_delivery_analytics_space_gs_026",),
        root_cause="plural_top_n_collapse",
    )
    assert diag["applicable"] is True
    assert diag["original_patch_type"] == "add_sql_snippet_expression"


def test_build_returns_qid_scoped_expression_when_flag_on(monkeypatch) -> None:
    monkeypatch.setenv("GSO_L6_NARROW_REPLACEMENT_FOR_EXPRESSION", "1")
    from genie_space_optimizer.optimization.cluster_driven_synthesis import (
        build_narrow_l6_replacement,
    )

    out = build_narrow_l6_replacement(
        original_patch=_h002_expression_patch(),
        ag_target_qids=("7now_delivery_analytics_space_gs_026",),
        root_cause="plural_top_n_collapse",
    )
    assert out is not None
    assert out["patch_type"] == "add_sql_snippet_expression"
    assert (
        "7now_delivery_analytics_space_gs_026"
        in out["sql_expression"]
    )
    assert out["narrowing_strategy"] == "expression_qid_scope"
    assert out["proposal_id"].endswith("_narrow")
    assert out["target"] == "mv_esr_dim_location.zone_vp_name"
    assert out["rationale"].startswith(
        "plural top-N collapse for zone-VP"
    )


def test_build_returns_qid_scoped_measure_when_flag_on(monkeypatch) -> None:
    monkeypatch.setenv("GSO_L6_NARROW_REPLACEMENT_FOR_EXPRESSION", "1")
    from genie_space_optimizer.optimization.cluster_driven_synthesis import (
        build_narrow_l6_replacement,
    )

    out = build_narrow_l6_replacement(
        original_patch=_h002_measure_patch(),
        ag_target_qids=("7now_delivery_analytics_space_gs_026",),
        root_cause="plural_top_n_collapse",
    )
    assert out is not None
    assert out["patch_type"] == "add_sql_snippet_measure"
    assert (
        "7now_delivery_analytics_space_gs_026"
        in out["sql_expression"]
    )
    assert out["narrowing_strategy"] == "expression_qid_scope"


def test_build_returns_none_for_expression_patch_when_flag_off(
    monkeypatch,
) -> None:
    """Byte-stability: flag-off path matches pre-P0 behavior."""
    monkeypatch.delenv(
        "GSO_L6_NARROW_REPLACEMENT_FOR_EXPRESSION", raising=False
    )
    from genie_space_optimizer.optimization.cluster_driven_synthesis import (
        build_narrow_l6_replacement,
    )

    out = build_narrow_l6_replacement(
        original_patch=_h002_expression_patch(),
        ag_target_qids=("7now_delivery_analytics_space_gs_026",),
        root_cause="plural_top_n_collapse",
    )
    assert out is None


def test_build_returns_none_when_target_qids_empty(monkeypatch) -> None:
    monkeypatch.setenv("GSO_L6_NARROW_REPLACEMENT_FOR_EXPRESSION", "1")
    from genie_space_optimizer.optimization.cluster_driven_synthesis import (
        build_narrow_l6_replacement,
    )

    out = build_narrow_l6_replacement(
        original_patch=_h002_expression_patch(),
        ag_target_qids=(),
        root_cause="plural_top_n_collapse",
    )
    assert out is None


def test_build_returns_none_when_sql_expression_empty(monkeypatch) -> None:
    monkeypatch.setenv("GSO_L6_NARROW_REPLACEMENT_FOR_EXPRESSION", "1")
    from genie_space_optimizer.optimization.cluster_driven_synthesis import (
        build_narrow_l6_replacement,
    )

    patch = {
        "proposal_id": "L6:Z#0",
        "patch_type": "add_sql_snippet_expression",
        "target": "x.y",
        "sql_expression": "",
        "rationale": "",
    }
    out = build_narrow_l6_replacement(
        original_patch=patch,
        ag_target_qids=("q",),
        root_cause="plural_top_n_collapse",
    )
    assert out is None


def test_diagnose_returns_existing_decline_for_unknown_patch_type(
    monkeypatch,
) -> None:
    """Byte-stability: unrecognized patch types still return False."""
    monkeypatch.setenv("GSO_L6_NARROW_REPLACEMENT_FOR_EXPRESSION", "1")
    from genie_space_optimizer.optimization.cluster_driven_synthesis import (
        narrow_replacement_diagnosis,
    )

    diag = narrow_replacement_diagnosis(
        original_patch={"patch_type": "make_up_a_thing"},
        ag_target_qids=("q",),
        root_cause="x",
    )
    assert diag["applicable"] is False
    assert diag["reason"] == "unrecognized_patch_type"


def test_flag_default_is_off(monkeypatch) -> None:
    monkeypatch.delenv(
        "GSO_L6_NARROW_REPLACEMENT_FOR_EXPRESSION", raising=False
    )
    from genie_space_optimizer.common.config import (
        l6_narrow_replacement_for_expression_enabled,
    )
    assert l6_narrow_replacement_for_expression_enabled() is False


def test_flag_truthy_values(monkeypatch) -> None:
    from genie_space_optimizer.common.config import (
        l6_narrow_replacement_for_expression_enabled,
    )
    for v in ("1", "true", "True", "yes", "on"):
        monkeypatch.setenv("GSO_L6_NARROW_REPLACEMENT_FOR_EXPRESSION", v)
        assert l6_narrow_replacement_for_expression_enabled() is True
