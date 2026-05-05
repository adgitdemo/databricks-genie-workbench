"""Cycle 10 W3.4 — typed outcomes when force-L6 yields nothing."""
from __future__ import annotations


def test_emit_force_l6_outcome_none(monkeypatch):
    monkeypatch.setenv("GSO_LEVER6_FORCE_TYPED_OUTCOMES", "1")
    from genie_space_optimizer.optimization.harness import (
        _emit_force_l6_outcome,
    )
    iter_inputs = {"decision_records": [], "markers": []}
    _emit_force_l6_outcome(
        outcome="declined",
        run_id="r1", iteration=2, ag_id="AG_X",
        cluster_id="H004", root_cause="missing_filter",
        target_qids=("gs_024",),
        exception_repr="",
        iter_inputs=iter_inputs,
    )
    rcs = [r["reason_code"] for r in iter_inputs["decision_records"]]
    assert "lever6_force_llm_declined" in rcs
    assert "proposal_generation_empty" in rcs
    assert any(
        m.startswith("GSO_LEVER6_FORCE_LLM_DECLINED_V1 ")
        for m in iter_inputs["markers"]
    )


def test_emit_force_l6_outcome_raised(monkeypatch):
    monkeypatch.setenv("GSO_LEVER6_FORCE_TYPED_OUTCOMES", "1")
    from genie_space_optimizer.optimization.harness import (
        _emit_force_l6_outcome,
    )
    iter_inputs = {"decision_records": [], "markers": []}
    _emit_force_l6_outcome(
        outcome="raised",
        run_id="r1", iteration=2, ag_id="AG_X",
        cluster_id="H004", root_cause="missing_filter",
        target_qids=(),
        exception_repr="ValueError('synthesis failed')",
        iter_inputs=iter_inputs,
    )
    rcs = [r["reason_code"] for r in iter_inputs["decision_records"]]
    assert "lever6_force_raised" in rcs
    assert any(
        m.startswith("GSO_LEVER6_FORCE_RAISED_V1 ")
        for m in iter_inputs["markers"]
    )


def test_emit_force_l6_outcome_flag_off_byte_stable(monkeypatch):
    monkeypatch.setenv("GSO_LEVER6_FORCE_TYPED_OUTCOMES", "0")
    from genie_space_optimizer.optimization.harness import (
        _emit_force_l6_outcome,
    )
    iter_inputs = {"decision_records": [], "markers": []}
    _emit_force_l6_outcome(
        outcome="declined",
        run_id="r1", iteration=2, ag_id="AG_X",
        cluster_id="H004", root_cause="missing_filter",
        target_qids=("gs_024",),
        exception_repr="",
        iter_inputs=iter_inputs,
    )
    assert iter_inputs["decision_records"] == []
    assert iter_inputs["markers"] == []
