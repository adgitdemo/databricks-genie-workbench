from __future__ import annotations

import time

import pytest

from genie_space_optimizer.optimization.eval_watchdog import (
    EvalHangTimeoutError,
    compute_eval_deadline_seconds,
    eval_watchdog_enabled,
    run_with_watchdog,
)


def test_watchdog_returns_value_when_callable_finishes_in_time():
    def _ok():
        return {"metrics": {"score": 1.0}}

    result = run_with_watchdog(_ok, deadline_seconds=2.0)
    assert result == {"metrics": {"score": 1.0}}


def test_watchdog_raises_eval_hang_timeout_error_when_callable_overruns():
    def _slow():
        time.sleep(2.0)
        return "done"

    with pytest.raises(EvalHangTimeoutError):
        run_with_watchdog(_slow, deadline_seconds=0.2, poll_interval=0.05)


def test_watchdog_propagates_inner_exception():
    class _Boom(RuntimeError):
        pass

    def _explode():
        raise _Boom("nope")

    with pytest.raises(_Boom):
        run_with_watchdog(_explode, deadline_seconds=2.0)


def test_eval_watchdog_default_on(monkeypatch):
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_WATCHDOG_ENABLED", raising=False)
    assert eval_watchdog_enabled() is True


def test_eval_watchdog_can_be_disabled(monkeypatch):
    monkeypatch.setenv("GENIE_SPACE_OPTIMIZER_EVAL_WATCHDOG_ENABLED", "false")
    assert eval_watchdog_enabled() is False


def test_compute_deadline_respects_floor():
    assert compute_eval_deadline_seconds(
        row_count=1, scorer_count=1, per_call_budget_seconds=10, floor_seconds=300
    ) == 300


def test_compute_deadline_respects_cap():
    assert compute_eval_deadline_seconds(
        row_count=1000, scorer_count=10, per_call_budget_seconds=90, cap_seconds=7200
    ) == 7200


def test_compute_deadline_uses_estimate_between_bounds():
    # 30 rows * 9 scorers * 90s = 24,300 -> floor 600, cap 7200 -> capped 7200
    # use a smaller scenario inside bounds:
    deadline = compute_eval_deadline_seconds(
        row_count=2, scorer_count=3, per_call_budget_seconds=90,
        floor_seconds=300, cap_seconds=7200,
    )
    assert deadline == 540  # 2*3*90
