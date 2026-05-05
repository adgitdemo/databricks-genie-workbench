"""Cycle 10 W2 — AG-levers union with cluster.recommended_levers."""
from __future__ import annotations


def test_union_adds_missing_recommended_levers():
    from genie_space_optimizer.optimization.control_plane import (
        union_ag_levers_with_recommended,
    )
    ag = {
        "id": "AG_DECOMPOSED_H001",
        "lever_directives": {
            "5": {"kind": "sql_shape", "root_cause": "missing_filter"},
        },
    }
    cluster = {
        "cluster_id": "H001",
        "recommended_levers": [3, 5, 6],
        "root_cause": "missing_filter",
    }
    out = union_ag_levers_with_recommended(ag=ag, cluster=cluster)
    assert set(out["lever_directives"].keys()) == {"3", "5", "6"}
    assert out["lever_directives"]["5"]["root_cause"] == "missing_filter"
    assert out["lever_directives"]["3"]["kind"] == "recommended_passthrough"
    assert out["lever_directives"]["6"]["kind"] == "recommended_passthrough"


def test_union_preserves_existing_directive_payloads():
    from genie_space_optimizer.optimization.control_plane import (
        union_ag_levers_with_recommended,
    )
    ag = {
        "id": "AG_X",
        "lever_directives": {
            "5": {"kind": "sql_shape", "root_cause": "missing_filter",
                  "guidance": "do thing"},
        },
    }
    cluster = {"cluster_id": "Hx", "recommended_levers": [5]}
    out = union_ag_levers_with_recommended(ag=ag, cluster=cluster)
    assert out["lever_directives"]["5"]["guidance"] == "do thing"
    assert out is not ag


def test_union_empty_recommended_returns_input_shape():
    from genie_space_optimizer.optimization.control_plane import (
        union_ag_levers_with_recommended,
    )
    ag = {"id": "AG_X", "lever_directives": {"5": {"kind": "sql_shape"}}}
    cluster = {"cluster_id": "Hx", "recommended_levers": []}
    out = union_ag_levers_with_recommended(ag=ag, cluster=cluster)
    assert out["lever_directives"] == {"5": {"kind": "sql_shape"}}


def test_union_handles_missing_lever_directives_block():
    from genie_space_optimizer.optimization.control_plane import (
        union_ag_levers_with_recommended,
    )
    ag = {"id": "AG_X"}
    cluster = {"cluster_id": "Hx", "recommended_levers": [3, 6]}
    out = union_ag_levers_with_recommended(ag=ag, cluster=cluster)
    assert set(out["lever_directives"].keys()) == {"3", "6"}


def test_diagnostic_action_group_unions_recommended_levers(monkeypatch):
    monkeypatch.setenv("GSO_AG_LEVERS_UNION_RECOMMENDED", "1")
    from genie_space_optimizer.optimization.control_plane import (
        diagnostic_action_group_for_cluster,
    )
    cluster = {
        "cluster_id": "H001",
        "root_cause": "missing_filter",
        "recommended_levers": [3, 5, 6],
        "question_ids": ["gs_009", "gs_024"],
        "asi_counterfactual_fixes": ["add WHERE outbound_total = 1"],
        "rca_id": "rca_abc",
    }
    ag = diagnostic_action_group_for_cluster(cluster)
    assert set(ag["lever_directives"].keys()) == {"3", "5", "6"}


def test_diagnostic_action_group_flag_off_byte_stable(monkeypatch):
    monkeypatch.setenv("GSO_AG_LEVERS_UNION_RECOMMENDED", "0")
    from genie_space_optimizer.optimization.control_plane import (
        diagnostic_action_group_for_cluster,
    )
    cluster = {
        "cluster_id": "H001",
        "root_cause": "missing_filter",
        "recommended_levers": [3, 5, 6],
        "question_ids": ["gs_009"],
        "rca_id": "rca_abc",
    }
    ag = diagnostic_action_group_for_cluster(cluster)
    assert set(ag["lever_directives"].keys()) == {"5"}


def test_union_records_levers_before():
    from genie_space_optimizer.optimization.control_plane import (
        union_ag_levers_with_recommended,
    )
    ag = {"lever_directives": {"5": {"kind": "sql_shape"}}}
    cluster = {"cluster_id": "H1", "recommended_levers": [3, 5, 6]}
    out = union_ag_levers_with_recommended(ag=ag, cluster=cluster)
    assert out["_levers_before_union"] == ["5"]
