"""Cycle 11 — _DIAGNOSTIC_AG_DIRECTIVES routes missing_filter to L6
(sql_snippet_filter), not L5 (instructions). Closes airline H004
and 7NOW H004/H005 cases where the diagnostic directive contradicted
cluster.recommended_levers."""

from __future__ import annotations


def test_diagnostic_ag_for_missing_filter_emits_lever_6_directive() -> None:
    from genie_space_optimizer.optimization.control_plane import (
        diagnostic_action_group_for_cluster,
    )

    cluster = {
        "cluster_id": "H004",
        "question_ids": ["q1"],
        "root_cause": "missing_filter",
        "asi_counterfactual_fixes": [
            "Remove unrequested PAYMENT_CURRENCY_CD = 'USD' filter",
        ],
        "recommended_levers": [3, 5, 6],
    }
    ag = diagnostic_action_group_for_cluster(cluster)
    directives = ag.get("lever_directives") or {}
    assert "6" in directives, directives
    assert directives["6"]["kind"] == "sql_snippet_filter"
    assert directives["6"]["root_cause"] == "missing_filter"
