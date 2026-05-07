"""Cycle 11 — strategist-emit AGs honour cluster.recommended_levers
via union_ag_levers_with_recommended. Until now the union was only
applied to coverage AGs, leaving 7NOW H002's primary path with
levers=[1,5] vs recommended=[3,5]."""

from __future__ import annotations


def test_strategist_ag_unions_recommended_levers_when_flag_on(monkeypatch) -> None:
    monkeypatch.delenv("GSO_AG_LEVERS_UNION_STRATEGIST_PATH", raising=False)
    monkeypatch.delenv("GSO_AG_LEVERS_UNION_RECOMMENDED", raising=False)

    from genie_space_optimizer.optimization.stages.action_groups import (
        normalize_strategist_ags_with_recommended_levers,
    )

    ags = [{
        "id": "AG1",
        "lever_directives": {"1": {"kind": "x"}, "5": {"kind": "y"}},
        "source_cluster_ids": ["H002"],
    }]
    clusters = [{
        "cluster_id": "H002",
        "recommended_levers": [3, 5],
        "root_cause": "plural_top_n_collapse",
        "question_ids": ["q1"],
    }]

    out = normalize_strategist_ags_with_recommended_levers(
        ags=ags, clusters=clusters,
    )
    assert len(out) == 1
    levers = set(out[0]["lever_directives"].keys())
    assert {"1", "3", "5"}.issubset(levers)


def test_strategist_ag_no_op_when_flag_off(monkeypatch) -> None:
    monkeypatch.setenv("GSO_AG_LEVERS_UNION_STRATEGIST_PATH", "0")
    from genie_space_optimizer.optimization.stages.action_groups import (
        normalize_strategist_ags_with_recommended_levers,
    )
    ags = [{
        "id": "AG1",
        "lever_directives": {"1": {"kind": "x"}},
        "source_cluster_ids": ["H002"],
    }]
    clusters = [{"cluster_id": "H002", "recommended_levers": [3, 5]}]
    out = normalize_strategist_ags_with_recommended_levers(
        ags=ags, clusters=clusters,
    )
    assert set(out[0]["lever_directives"].keys()) == {"1"}


def test_ag_levers_union_strategist_path_flag_default_on(monkeypatch) -> None:
    monkeypatch.delenv("GSO_AG_LEVERS_UNION_STRATEGIST_PATH", raising=False)
    from genie_space_optimizer.common.config import (
        ag_levers_union_strategist_path_enabled,
    )
    assert ag_levers_union_strategist_path_enabled() is True
