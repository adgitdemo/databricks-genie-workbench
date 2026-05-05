"""Cycle 10 W1.2 — RCA-ungrounded wiring in harness."""
from __future__ import annotations


def _stub_iter_inputs():
    return {"decision_records": [], "markers": []}


def test_rca_ungrounded_record_emitted_for_unfit_cluster(monkeypatch):
    monkeypatch.setenv("GSO_RCA_UNGROUNDED_RECORDS_ENABLED", "1")
    from genie_space_optimizer.optimization.harness import (
        _emit_rca_ungrounded_records_for_unfit_clusters,
    )
    iter_inputs = _stub_iter_inputs()
    cluster = {
        "cluster_id": "H001",
        "root_cause": "missing_filter",
        "question_ids": ["gs_009", "gs_024"],
    }
    n = _emit_rca_ungrounded_records_for_unfit_clusters(
        run_id="r1",
        iteration=2,
        clusters=[cluster],
        rca_id_by_cluster={"H001": ""},
        ag_emitted_for_cluster={"H001": True},
        iter_inputs=iter_inputs,
    )
    assert n == 1
    assert any(
        rec.get("reason_code") == "rca_ungrounded"
        for rec in iter_inputs["decision_records"]
    )


def test_rca_ungrounded_record_flag_off_preserves_legacy(monkeypatch):
    monkeypatch.setenv("GSO_RCA_UNGROUNDED_RECORDS_ENABLED", "0")
    from genie_space_optimizer.optimization.harness import (
        _emit_rca_ungrounded_records_for_unfit_clusters,
    )
    iter_inputs = _stub_iter_inputs()
    cluster = {
        "cluster_id": "H001",
        "root_cause": "missing_filter",
        "question_ids": ["gs_009"],
    }
    n = _emit_rca_ungrounded_records_for_unfit_clusters(
        run_id="r1",
        iteration=2,
        clusters=[cluster],
        rca_id_by_cluster={"H001": ""},
        ag_emitted_for_cluster={"H001": True},
        iter_inputs=iter_inputs,
    )
    assert n == 0
    assert iter_inputs["decision_records"] == []


def test_rca_ungrounded_skipped_when_cluster_has_fit_rca(monkeypatch):
    monkeypatch.setenv("GSO_RCA_UNGROUNDED_RECORDS_ENABLED", "1")
    from genie_space_optimizer.optimization.harness import (
        _emit_rca_ungrounded_records_for_unfit_clusters,
    )
    iter_inputs = _stub_iter_inputs()
    cluster = {
        "cluster_id": "H002",
        "root_cause": "missing_filter",
        "question_ids": ["gs_005"],
    }
    n = _emit_rca_ungrounded_records_for_unfit_clusters(
        run_id="r1",
        iteration=2,
        clusters=[cluster],
        rca_id_by_cluster={"H002": "rca_abc123"},
        ag_emitted_for_cluster={"H002": True},
        iter_inputs=iter_inputs,
    )
    assert n == 0
