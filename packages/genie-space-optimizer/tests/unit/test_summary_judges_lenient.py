"""Plan N4 Task 8 — pin the lenient ``_build_summary_row`` path.

Plan name: ``_summary_judges_or_raise``. Actual function:
``evaluation._build_summary_row``. The function only raises when
``GSO_ASSERT_ROW_CANONICAL=1`` is set (off in production today);
bringing it into the policy guarantees that an accidental flip of
that env var on a production app cannot crash a run. Operators
who want strict-debug behaviour set both
``GSO_ASSERT_ROW_CANONICAL=1`` AND ``GSO_INVARIANT_STRICT=1``.
"""
from __future__ import annotations

import pytest


def test_lenient_non_canonical_row_logs_and_returns(monkeypatch) -> None:
    """With ``GSO_ASSERT_ROW_CANONICAL=1`` and lenient invariant
    mode, a non-canonical row (verdict present, rationale empty)
    invokes the lenient callback once per non-canonical judge and
    returns the per-judge view with the empty rationale preserved."""
    from genie_space_optimizer.optimization.evaluation import (
        _build_summary_row,
    )

    monkeypatch.setenv("GSO_ASSERT_ROW_CANONICAL", "1")
    monkeypatch.delenv("GSO_INVARIANT_STRICT", raising=False)
    monkeypatch.delenv("GSO_DECISION_EMITTER_STRICT", raising=False)

    captured: list = []
    out = _build_summary_row(
        row_dict={
            "result_correctness/value": "yes",
            "result_correctness/rationale": "",
        },
        on_violation=lambda v: captured.append(v),
    )
    # No raise; output still contains the row with empty rationale.
    assert any(
        j["judge"] == "result_correctness" and j["value"] == "yes"
        and j["rationale"] == ""
        for j in out
    )
    # Lenient callback received a violation for the missing rationale.
    assert len(captured) >= 1
    assert captured[0].name == "non_canonical_judge_row"


def test_strict_mode_with_canonical_assert_still_raises(monkeypatch) -> None:
    """Both ``GSO_ASSERT_ROW_CANONICAL=1`` and ``GSO_INVARIANT_STRICT=1``
    must raise so CI / debug runs catch the underlying merge bug."""
    from genie_space_optimizer.optimization.evaluation import (
        _build_summary_row,
    )

    monkeypatch.setenv("GSO_ASSERT_ROW_CANONICAL", "1")
    monkeypatch.setenv("GSO_INVARIANT_STRICT", "1")
    with pytest.raises(AssertionError, match="non_canonical_judge_row"):
        _build_summary_row(
            row_dict={
                "result_correctness/value": "yes",
                "result_correctness/rationale": "",
            },
        )


def test_default_off_path_unchanged(monkeypatch) -> None:
    """When ``GSO_ASSERT_ROW_CANONICAL`` is unset (production
    default), no callback fires and the function returns the merged
    summary without raising."""
    from genie_space_optimizer.optimization.evaluation import (
        _build_summary_row,
    )

    monkeypatch.delenv("GSO_ASSERT_ROW_CANONICAL", raising=False)
    captured: list = []
    out = _build_summary_row(
        row_dict={
            "result_correctness/value": "yes",
            "result_correctness/rationale": "",
        },
        on_violation=lambda v: captured.append(v),
    )
    assert out
    assert captured == []  # callback not fired when env var off
