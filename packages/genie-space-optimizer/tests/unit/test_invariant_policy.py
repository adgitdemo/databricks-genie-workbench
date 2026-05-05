"""Plan N4 Task 1 — pin the invariant-policy module contract.

The lever loop has three invariants that historically raised
``AssertionError`` and aborted the run on the first drift event:

- ``assert_quarantine_attribution_sound``
- ``assert_regression_debt_partition_complete``
- ``assert_soft_cluster_currency``

Plus two structural-integrity sites (``_assert_cap_conservation`` in
patch_selection, ``_summary_judges_or_raise`` in evaluation). All
five route through a single policy module so production deploys
degrade gracefully while CI / replay keeps the loud failure mode.
"""
from __future__ import annotations

import pytest


def test_is_invariant_strict_mode_reads_dedicated_var(monkeypatch) -> None:
    from genie_space_optimizer.optimization.invariant_policy import (
        is_invariant_strict_mode,
    )
    monkeypatch.setenv("GSO_INVARIANT_STRICT", "1")
    monkeypatch.delenv("GSO_DECISION_EMITTER_STRICT", raising=False)
    assert is_invariant_strict_mode() is True


def test_is_invariant_strict_mode_falls_back_to_decision_emitter_var(
    monkeypatch,
) -> None:
    from genie_space_optimizer.optimization.invariant_policy import (
        is_invariant_strict_mode,
    )
    monkeypatch.delenv("GSO_INVARIANT_STRICT", raising=False)
    monkeypatch.setenv("GSO_DECISION_EMITTER_STRICT", "1")
    assert is_invariant_strict_mode() is True


def test_is_invariant_strict_mode_default_is_false(monkeypatch) -> None:
    from genie_space_optimizer.optimization.invariant_policy import (
        is_invariant_strict_mode,
    )
    monkeypatch.delenv("GSO_INVARIANT_STRICT", raising=False)
    monkeypatch.delenv("GSO_DECISION_EMITTER_STRICT", raising=False)
    assert is_invariant_strict_mode() is False


def test_handle_invariant_violation_strict_raises() -> None:
    from genie_space_optimizer.optimization.invariant_policy import (
        InvariantViolation,
        handle_invariant_violation,
    )
    v = InvariantViolation(
        name="quarantine_attribution_drift",
        payload={"qids": ("gs_009",)},
        message="passing qid in quarantine",
    )
    with pytest.raises(AssertionError) as exc:
        handle_invariant_violation(
            v, strict=True, lenient_callback=lambda x: None,
        )
    assert "quarantine_attribution_drift" in str(exc.value)


def test_handle_invariant_violation_lenient_calls_callback_and_returns() -> None:
    from genie_space_optimizer.optimization.invariant_policy import (
        InvariantViolation,
        handle_invariant_violation,
    )
    captured: list = []
    v = InvariantViolation(
        name="x",
        payload={"k": "v"},
        message="m",
    )
    handle_invariant_violation(
        v, strict=False,
        lenient_callback=lambda violation: captured.append(violation),
    )
    assert len(captured) == 1
    assert captured[0].name == "x"


def test_invariant_violation_payload_is_immutable_after_construction() -> None:
    from genie_space_optimizer.optimization.invariant_policy import (
        InvariantViolation,
    )
    v = InvariantViolation(
        name="x", payload={"a": 1}, message="m",
    )
    with pytest.raises(Exception):
        v.payload["a"] = 2  # frozen / Mapping
