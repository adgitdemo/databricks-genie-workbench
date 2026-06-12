"""Cycle 10 W2.4 — decomposer unions levers with cluster.recommended_levers."""
from __future__ import annotations


def test_decompose_overbroad_ag_unions_levers(monkeypatch):
    monkeypatch.setenv("GSO_AG_LEVERS_UNION_RECOMMENDED", "1")
    from genie_space_optimizer.optimization.control_plane import (
        decompose_overbroad_ag,
    )
    parent_ag = {
        "id": "AG_BROAD",
        "lever_directives": {
            "5": {"kind": "sql_shape", "root_cause": "missing_filter"},
        },
        "source_cluster_ids": ["H001", "H004"],
        "affected_questions": ["gs_009", "gs_024"],
    }
    # Distinct root_cause families trigger decomposition.
    clusters = [
        {"cluster_id": "H001", "root_cause": "missing_filter",
         "recommended_levers": [3, 5, 6], "question_ids": ["gs_009"],
         "rca_id": "r1"},
        {"cluster_id": "H004", "root_cause": "wrong_aggregation",
         "recommended_levers": [3, 5, 6], "question_ids": ["gs_024"],
         "rca_id": "r2"},
    ]
    children = decompose_overbroad_ag(parent_ag, clusters)
    assert len(children) == 2
    for child in children:
        assert set(child["lever_directives"].keys()) >= {"3", "5", "6"}


def test_decompose_overbroad_ag_flag_off_preserves_inheritance(monkeypatch):
    monkeypatch.setenv("GSO_AG_LEVERS_UNION_RECOMMENDED", "0")
    from genie_space_optimizer.optimization.control_plane import (
        decompose_overbroad_ag,
    )
    parent_ag = {
        "id": "AG_BROAD",
        "lever_directives": {"5": {"kind": "sql_shape"}},
        "source_cluster_ids": ["H001", "H004"],
        "affected_questions": ["gs_009", "gs_024"],
    }
    clusters = [
        {"cluster_id": "H001", "root_cause": "missing_filter",
         "recommended_levers": [3, 5, 6], "question_ids": ["gs_009"],
         "rca_id": "r1"},
        {"cluster_id": "H004", "root_cause": "wrong_aggregation",
         "recommended_levers": [3, 5, 6], "question_ids": ["gs_024"],
         "rca_id": "r2"},
    ]
    children = decompose_overbroad_ag(parent_ag, clusters)
    # With flag off, only the diagnostic-directive lever appears.
    for child in children:
        if "lever_directives" in child:
            assert "3" not in child.get("lever_directives", {})
