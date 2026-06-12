"""Cycle 10 W2.5 — AG-emit prompt enforces recommended-levers superset."""
from __future__ import annotations


def test_ag_emit_prompt_includes_recommended_levers_clause(monkeypatch):
    monkeypatch.setenv("GSO_AG_LEVERS_UNION_RECOMMENDED", "1")
    from genie_space_optimizer.optimization.strategist import (
        build_ag_emit_prompt_clusters_block,
    )
    clusters = [{
        "cluster_id": "H001",
        "root_cause": "missing_filter",
        "recommended_levers": [3, 5, 6],
        "question_ids": ["gs_009"],
    }]
    block = build_ag_emit_prompt_clusters_block(clusters)
    assert "recommended_levers" in block
    assert "3" in block and "5" in block and "6" in block
    assert (
        "Levers must include every lever in recommended_levers"
        in block
    )


def test_ag_emit_prompt_flag_off_omits_clause(monkeypatch):
    monkeypatch.setenv("GSO_AG_LEVERS_UNION_RECOMMENDED", "0")
    from genie_space_optimizer.optimization.strategist import (
        build_ag_emit_prompt_clusters_block,
    )
    clusters = [{
        "cluster_id": "H001",
        "root_cause": "missing_filter",
        "recommended_levers": [3, 5, 6],
        "question_ids": ["gs_009"],
    }]
    block = build_ag_emit_prompt_clusters_block(clusters)
    assert (
        "Levers must include every lever in recommended_levers"
        not in block
    )
