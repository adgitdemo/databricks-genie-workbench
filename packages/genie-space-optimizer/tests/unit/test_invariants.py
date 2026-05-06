"""Cycle 11 — invariant-suite tests. One test per invariant, each
exercises the pure function on synthetic inputs.

I1: phase_b.total_records >= replay_fixture.records
"""

from __future__ import annotations


def test_run_invariants_returns_empty_for_clean_run() -> None:
    from genie_space_optimizer.optimization.invariants import run_invariants

    evidence = {
        "phase_b": {"total_records": 20, "producer_exceptions": {}},
        "replay_fixture_records": 12,
        "iterations": [],
        "manifest": {"declared_paths": [], "materialized_paths": []},
        "convergence": {"reason": "lever_loop_completed"},
    }
    violations = run_invariants(evidence)
    assert violations == []


def test_i1_red_when_phase_b_total_below_replay_records() -> None:
    from genie_space_optimizer.optimization.invariants import check_i1_phase_b_records_present

    evidence = {
        "phase_b": {"total_records": 0, "producer_exceptions": {"ag_outcome": 2}},
        "replay_fixture_records": 12,
    }
    violations = check_i1_phase_b_records_present(evidence)
    assert len(violations) == 1
    v = violations[0]
    assert v["invariant_id"] == "I1"
    assert v["phase_b_total_records"] == 0
    assert v["replay_fixture_records"] == 12


def test_i1_green_when_phase_b_total_meets_replay_records() -> None:
    from genie_space_optimizer.optimization.invariants import check_i1_phase_b_records_present

    evidence = {
        "phase_b": {"total_records": 24, "producer_exceptions": {}},
        "replay_fixture_records": 24,
    }
    assert check_i1_phase_b_records_present(evidence) == []


def test_loop_invariants_flag_default_on(monkeypatch) -> None:
    monkeypatch.delenv("GSO_LOOP_INVARIANTS_ENABLED", raising=False)
    from genie_space_optimizer.common.config import loop_invariants_enabled
    assert loop_invariants_enabled() is True


def test_loop_invariants_strict_flag_default_on(monkeypatch) -> None:
    monkeypatch.delenv("GSO_LOOP_INVARIANTS_STRICT", raising=False)
    from genie_space_optimizer.common.config import loop_invariants_strict
    assert loop_invariants_strict() is True
