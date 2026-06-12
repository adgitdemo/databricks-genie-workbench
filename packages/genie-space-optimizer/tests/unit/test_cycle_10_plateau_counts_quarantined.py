"""Cycle 10 W6.2 — plateau guard counts convergence-quarantined qids."""
from __future__ import annotations


def test_compute_current_hard_qids_includes_quarantined(monkeypatch):
    monkeypatch.setenv("GSO_PLATEAU_COUNTS_QUARANTINED", "1")
    from genie_space_optimizer.optimization.harness import (
        compute_current_hard_qids,
    )
    out = compute_current_hard_qids(
        currently_failing=frozenset({"gs_013"}),
        convergence_quarantined=frozenset({"gs_009", "gs_024"}),
        retired_by_sql_delta=frozenset(),
        debt=frozenset(),
    )
    assert out == frozenset({"gs_009", "gs_013", "gs_024"})


def test_compute_current_hard_qids_excludes_retired(monkeypatch):
    monkeypatch.setenv("GSO_PLATEAU_COUNTS_QUARANTINED", "1")
    from genie_space_optimizer.optimization.harness import (
        compute_current_hard_qids,
    )
    out = compute_current_hard_qids(
        currently_failing=frozenset(),
        convergence_quarantined=frozenset({"gs_009", "gs_024"}),
        retired_by_sql_delta=frozenset({"gs_009"}),
        debt=frozenset(),
    )
    assert out == frozenset({"gs_024"})


def test_compute_current_hard_qids_flag_off_excludes_quarantined(monkeypatch):
    monkeypatch.setenv("GSO_PLATEAU_COUNTS_QUARANTINED", "0")
    from genie_space_optimizer.optimization.harness import (
        compute_current_hard_qids,
    )
    out = compute_current_hard_qids(
        currently_failing=frozenset({"gs_013"}),
        convergence_quarantined=frozenset({"gs_009", "gs_024"}),
        retired_by_sql_delta=frozenset(),
        debt=frozenset(),
    )
    assert out == frozenset({"gs_013"})
