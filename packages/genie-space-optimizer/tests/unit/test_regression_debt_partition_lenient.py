"""Plan N4 Task 5 — pin the lenient regression-debt-partition path.

The strict invariant raises when ``out_of_target_regressed_qids`` is
not the disjoint union of ``soft_to_hard / passing_to_hard /
unknown_to_hard``. In production, partition completeness is a
bookkeeping concern — a missing bucket attribution is a postmortem
gap, not a runtime correctness failure. The lenient path emits a
typed record + marker so the gap is auditable but the run continues.
"""
from __future__ import annotations

import pytest


def _make_decision(
    *,
    out_of_target=(),
    soft_to_hard=(),
    passing_to_hard=(),
    unknown_to_hard=(),
):
    """Build a ``ControlPlaneAcceptance`` with the partition fields
    set; other fields default to safe values. The harness helper
    only reads the four partition tuples.
    """
    from genie_space_optimizer.optimization.control_plane import (
        ControlPlaneAcceptance,
    )

    return ControlPlaneAcceptance(
        accepted=True,
        reason_code="accepted",
        baseline_accuracy=0.0,
        candidate_accuracy=0.0,
        delta_pp=0.0,
        target_qids=(),
        target_fixed_qids=(),
        target_still_hard_qids=(),
        out_of_target_regressed_qids=tuple(out_of_target),
        soft_to_hard_regressed_qids=tuple(soft_to_hard),
        passing_to_hard_regressed_qids=tuple(passing_to_hard),
        unknown_to_hard_regressed_qids=tuple(unknown_to_hard),
    )


def test_lenient_incomplete_partition_emits_record_and_marker_no_raise() -> None:
    """When the partition is incomplete (qids in
    ``out_of_target_regressed_qids`` but missing from every sub-
    bucket), the lenient path emits a typed record + marker and
    returns. Acceptance outcome is unchanged."""
    from genie_space_optimizer.optimization.harness import (
        _enforce_regression_debt_partition_invariant,
    )

    decision = _make_decision(
        out_of_target=("gs_021", "gs_013"),
        soft_to_hard=("gs_021",),
        # gs_013 is missing from every sub-bucket.
    )
    emitted_records: list = []
    emitted_markers: list = []

    _enforce_regression_debt_partition_invariant(
        decision=decision,
        run_id="r1",
        iteration=2,
        emit_record=emitted_records.append,
        emit_marker=emitted_markers.append,
        strict=False,
    )

    assert len(emitted_records) == 1
    rec = emitted_records[0]
    assert rec.reason_code.value == "regression_debt_partition_incomplete"
    assert "gs_013" in rec.target_qids
    assert any(
        "GSO_INVARIANT_VIOLATION_V1" in m
        and "regression_debt_partition_incomplete" in m
        for m in emitted_markers
    )


def test_strict_incomplete_partition_still_raises() -> None:
    from genie_space_optimizer.optimization.harness import (
        _enforce_regression_debt_partition_invariant,
    )

    decision = _make_decision(
        out_of_target=("gs_013",),
    )
    with pytest.raises(AssertionError, match="regression"):
        _enforce_regression_debt_partition_invariant(
            decision=decision,
            run_id="r1",
            iteration=2,
            emit_record=lambda r: None,
            emit_marker=lambda m: None,
            strict=True,
        )


def test_lenient_complete_partition_silent() -> None:
    """When the partition is complete and disjoint, the helper is
    silent — no record, no marker, no raise."""
    from genie_space_optimizer.optimization.harness import (
        _enforce_regression_debt_partition_invariant,
    )

    decision = _make_decision(
        out_of_target=("gs_021", "gs_013"),
        soft_to_hard=("gs_021",),
        passing_to_hard=("gs_013",),
    )
    emitted_records: list = []
    emitted_markers: list = []

    _enforce_regression_debt_partition_invariant(
        decision=decision,
        run_id="r1",
        iteration=2,
        emit_record=emitted_records.append,
        emit_marker=emitted_markers.append,
        strict=False,
    )

    assert emitted_records == []
    assert emitted_markers == []
