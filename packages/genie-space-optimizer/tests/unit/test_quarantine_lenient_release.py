"""Plan N4 Task 4 — pin the lenient quarantine-attribution path.

Trigger run 2026-05-05 06:56:03 UTC: ``gs_009`` was quarantined by
the pre-loop arbiter; an in-loop side-effect patch in a different
cluster moved it into the passing set. The strict invariant fired
and crashed the run. The lenient path recognises this as a desirable
end state, releases the qid from quarantine so the next iteration
starts consistent, and emits a typed record + marker.
"""
from __future__ import annotations

import pytest


def test_lenient_quarantine_release_drops_recovered_qids_and_emits_record() -> None:
    """When a quarantined qid is currently passing, the lenient
    path drops it from ``correction_state["quarantined_qids"]``,
    emits a ``QID_RELEASED_FROM_QUARANTINE`` decision record, and
    emits a ``GSO_INVARIANT_VIOLATION_V1`` marker.
    """
    from genie_space_optimizer.optimization.harness import (
        _enforce_quarantine_attribution_invariant,
    )

    correction_state = {"quarantined_qids": {"gs_009", "gs_012"}}
    emitted_records: list = []
    emitted_markers: list = []

    _enforce_quarantine_attribution_invariant(
        correction_state=correction_state,
        currently_passing_qids={"gs_009"},
        currently_hard_qids={"gs_012"},
        run_id="r1",
        iteration=2,
        emit_record=emitted_records.append,
        emit_marker=emitted_markers.append,
        strict=False,
    )

    # gs_009 released, gs_012 still quarantined.
    assert correction_state["quarantined_qids"] == {"gs_012"}
    assert len(emitted_records) == 1
    rec = emitted_records[0]
    assert rec.target_qids == ("gs_009",)
    assert rec.reason_code.value == "qid_released_from_quarantine"
    assert any(
        "GSO_INVARIANT_VIOLATION_V1" in m and "gs_009" in m
        for m in emitted_markers
    )


def test_strict_quarantine_attribution_still_raises() -> None:
    """Strict mode preserves the legacy ``AssertionError`` for CI /
    replay tooling that wants the loud failure mode."""
    from genie_space_optimizer.optimization.harness import (
        _enforce_quarantine_attribution_invariant,
    )

    with pytest.raises(AssertionError, match="quarantine_attribution_drift"):
        _enforce_quarantine_attribution_invariant(
            correction_state={"quarantined_qids": {"gs_009"}},
            currently_passing_qids={"gs_009"},
            currently_hard_qids=set(),
            run_id="r1",
            iteration=2,
            emit_record=lambda r: None,
            emit_marker=lambda m: None,
            strict=True,
        )


def test_no_drift_no_emit() -> None:
    """When the quarantine is sound, the helper neither raises nor
    emits anything — the lenient path is silent on success."""
    from genie_space_optimizer.optimization.harness import (
        _enforce_quarantine_attribution_invariant,
    )

    correction_state = {"quarantined_qids": {"gs_012"}}
    emitted_records: list = []
    emitted_markers: list = []

    _enforce_quarantine_attribution_invariant(
        correction_state=correction_state,
        currently_passing_qids={"gs_001", "gs_002"},  # no overlap
        currently_hard_qids={"gs_012", "gs_021"},
        run_id="r1",
        iteration=2,
        emit_record=emitted_records.append,
        emit_marker=emitted_markers.append,
        strict=False,
    )

    assert correction_state["quarantined_qids"] == {"gs_012"}
    assert emitted_records == []
    assert emitted_markers == []


def test_lenient_singleton_hard_releases_quarantine() -> None:
    """The singleton-hard invariant: when only one hard qid remains
    and it is quarantined, the lenient path releases it so the
    strategist still has a target to work on."""
    from genie_space_optimizer.optimization.harness import (
        _enforce_quarantine_attribution_invariant,
    )

    correction_state = {"quarantined_qids": {"gs_solo"}}
    emitted_records: list = []
    emitted_markers: list = []

    _enforce_quarantine_attribution_invariant(
        correction_state=correction_state,
        currently_passing_qids=set(),
        currently_hard_qids={"gs_solo"},  # singleton hard, also quarantined
        run_id="r1",
        iteration=2,
        emit_record=emitted_records.append,
        emit_marker=emitted_markers.append,
        strict=False,
    )

    # Released so strategist has a target.
    assert "gs_solo" not in correction_state["quarantined_qids"]
    assert len(emitted_records) == 1
    assert any("singleton" in m or "gs_solo" in m for m in emitted_markers)
