"""Cycle 10 W7.2 — single-source proposal-consumed flag."""
from __future__ import annotations


def test_compute_consumed_true_when_applied(monkeypatch):
    monkeypatch.setenv("GSO_PROPOSAL_TRACE_ONE_SOURCE", "1")
    from genie_space_optimizer.optimization.harness import (
        compute_proposal_consumed_flag,
    )
    proposal = {"proposal_id": "P001"}
    applied_ids = frozenset({"P001"})
    assert compute_proposal_consumed_flag(
        proposal=proposal,
        applied_proposal_ids=applied_ids,
        blast_dropped_proposal_ids=frozenset(),
        rca_dropped_proposal_ids=frozenset(),
    ) is True


def test_compute_consumed_false_when_blast_dropped(monkeypatch):
    monkeypatch.setenv("GSO_PROPOSAL_TRACE_ONE_SOURCE", "1")
    from genie_space_optimizer.optimization.harness import (
        compute_proposal_consumed_flag,
    )
    assert compute_proposal_consumed_flag(
        proposal={"proposal_id": "P002"},
        applied_proposal_ids=frozenset(),
        blast_dropped_proposal_ids=frozenset({"P002"}),
        rca_dropped_proposal_ids=frozenset(),
    ) is False


def test_compute_consumed_false_when_rca_dropped(monkeypatch):
    monkeypatch.setenv("GSO_PROPOSAL_TRACE_ONE_SOURCE", "1")
    from genie_space_optimizer.optimization.harness import (
        compute_proposal_consumed_flag,
    )
    assert compute_proposal_consumed_flag(
        proposal={"proposal_id": "P003"},
        applied_proposal_ids=frozenset(),
        blast_dropped_proposal_ids=frozenset(),
        rca_dropped_proposal_ids=frozenset({"P003"}),
    ) is False


def test_compute_consumed_flag_off_returns_legacy_default(monkeypatch):
    monkeypatch.setenv("GSO_PROPOSAL_TRACE_ONE_SOURCE", "0")
    from genie_space_optimizer.optimization.harness import (
        compute_proposal_consumed_flag,
    )
    # Legacy semantics: consumed iff applied (matches what was
    # documented as the post-strategist trace's view).
    assert compute_proposal_consumed_flag(
        proposal={"proposal_id": "P001"},
        applied_proposal_ids=frozenset({"P001"}),
        blast_dropped_proposal_ids=frozenset(),
        rca_dropped_proposal_ids=frozenset(),
    ) is True


def test_compute_consumed_returns_false_for_missing_proposal_id():
    from genie_space_optimizer.optimization.harness import (
        compute_proposal_consumed_flag,
    )
    assert compute_proposal_consumed_flag(
        proposal={},
        applied_proposal_ids=frozenset({"P001"}),
        blast_dropped_proposal_ids=frozenset(),
        rca_dropped_proposal_ids=frozenset(),
    ) is False
