"""P0 Task 5A: pin the narrow_replacement_synthesized record + marker."""

from __future__ import annotations


def test_narrow_replacement_synthesized_record_shape() -> None:
    from genie_space_optimizer.optimization.decision_emitters import (
        narrow_replacement_synthesized_record,
    )

    rec = narrow_replacement_synthesized_record(
        run_id="r1",
        iteration=1,
        ag_id="AG1",
        cluster_id="H002",
        root_cause="plural_top_n_collapse",
        original_patch_type="add_sql_snippet_expression",
        original_proposal_id="L6:P001#3",
        narrow_proposal_id="L6:P001#3_narrow",
        narrowing_strategy="expression_qid_scope",
        target_qids=("7now_delivery_analytics_space_gs_026",),
    )
    d = rec.to_dict()
    assert d["decision_type"] == "narrow_replacement_synthesized"
    assert d["ag_id"] == "AG1"
    assert d["cluster_id"] == "H002"
    assert d["narrowing_strategy"] == "expression_qid_scope"
    assert d["original_proposal_id"] == "L6:P001#3"
    assert d["narrow_proposal_id"] == "L6:P001#3_narrow"
    assert list(d["target_qids"]) == [
        "7now_delivery_analytics_space_gs_026"
    ]


def test_narrow_replacement_synthesized_marker_shape() -> None:
    from genie_space_optimizer.common.mlflow_markers import (
        narrow_replacement_synthesized_marker,
    )

    m = narrow_replacement_synthesized_marker(
        run_id="r1",
        iteration=1,
        ag_id="AG1",
        cluster_id="H002",
        root_cause="plural_top_n_collapse",
        original_patch_type="add_sql_snippet_expression",
        narrowing_strategy="expression_qid_scope",
        narrow_proposal_id="L6:P001#3_narrow",
    )
    assert m.startswith("GSO_NARROW_REPLACEMENT_SYNTHESIZED_V1")
    assert "AG1" in m
    assert "expression_qid_scope" in m
