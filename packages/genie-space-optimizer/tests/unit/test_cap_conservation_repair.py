"""Plan N4 Task 7 — pin the cap-conservation reconcile path.

The strict ``_assert_cap_conservation`` raises when a cap selector
returns a decision-list count that doesn't match the input count, or
when ``selected + dropped != input``. In production we reconcile —
truncate extras, pad missing slots with explicit
``decision="dropped"`` entries carrying
``reason="cap_conservation_repaired"`` — so the survival ledger
downstream sees a typed dropped-decision rather than a count
mismatch and the run continues.

Strict mode preserves the legacy ``AssertionError`` for CI / replay
to surface the underlying selector bug.
"""
from __future__ import annotations

import pytest


def test_reconcile_truncates_extras_to_input_count() -> None:
    from genie_space_optimizer.optimization.patch_selection import (
        reconcile_cap_conservation,
    )

    decisions = [
        {"id": "a", "decision": "selected"},
        {"id": "b", "decision": "selected"},
        {"id": "c", "decision": "selected"},
    ]
    repaired = reconcile_cap_conservation(decisions=decisions, input_count=2)
    assert len(repaired) == 2
    assert [d["id"] for d in repaired] == ["a", "b"]


def test_reconcile_pads_missing_slots_with_typed_dropped_reason() -> None:
    from genie_space_optimizer.optimization.patch_selection import (
        reconcile_cap_conservation,
    )

    decisions = [{"id": "a", "decision": "selected"}]
    repaired = reconcile_cap_conservation(decisions=decisions, input_count=3)
    assert len(repaired) == 3
    assert repaired[0]["id"] == "a"
    for pad in repaired[1:]:
        assert pad["decision"] == "dropped"
        assert pad["reason"] == "cap_conservation_repaired"


def test_reconcile_passes_through_when_count_matches() -> None:
    from genie_space_optimizer.optimization.patch_selection import (
        reconcile_cap_conservation,
    )

    decisions = [
        {"id": "a", "decision": "selected"},
        {"id": "b", "decision": "dropped"},
    ]
    repaired = reconcile_cap_conservation(decisions=decisions, input_count=2)
    assert repaired == decisions


def test_assert_cap_conservation_lenient_callback_invoked_no_raise() -> None:
    from genie_space_optimizer.optimization.patch_selection import (
        _assert_cap_conservation,
    )

    captured: list = []
    _assert_cap_conservation(
        decisions=[{"id": "a", "decision": "selected"}],
        input_count=2,
        func_name="select_under_cap",
        on_violation=lambda v: captured.append(v),
    )
    assert len(captured) == 1
    assert captured[0].name == "cap_conservation_violated"


def test_assert_cap_conservation_default_still_raises() -> None:
    from genie_space_optimizer.optimization.patch_selection import (
        _assert_cap_conservation,
    )

    with pytest.raises(AssertionError, match="cap_conservation_violated"):
        _assert_cap_conservation(
            decisions=[{"id": "a", "decision": "selected"}],
            input_count=2,
            func_name="select_under_cap",
        )


def test_assert_cap_conservation_lenient_kept_dropped_mismatch() -> None:
    from genie_space_optimizer.optimization.patch_selection import (
        _assert_cap_conservation,
    )

    captured: list = []
    _assert_cap_conservation(
        decisions=[
            {"id": "a", "decision": "selected"},
            {"id": "b", "decision": "unrecognized"},
        ],
        input_count=2,
        func_name="select_under_cap",
        on_violation=lambda v: captured.append(v),
    )
    assert len(captured) == 1
    assert captured[0].name == "cap_conservation_violated"
    assert captured[0].payload.get("kind") == "kept_dropped_mismatch"
