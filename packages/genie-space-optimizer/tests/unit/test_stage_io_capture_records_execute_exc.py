"""Cycle 11 — when wrap_with_io_capture's wrapped execute() raises,
``_CAPTURE_FAILURES`` must record an entry so the harness manifest
reflects the loss. Closes the 7NOW manifest.missing_pieces=[] /
130-of-163-missing inconsistency.
"""

from __future__ import annotations

import pytest


def test_execute_exc_recorded_in_capture_failures(monkeypatch) -> None:
    from genie_space_optimizer.optimization import stage_io_capture as sic

    sic.consume_capture_failures()

    class _Ctx:
        mlflow_anchor_run_id = None
        iteration = 1
        decision_emit = staticmethod(lambda r: None)

    def _execute(_ctx, _inp):
        raise RuntimeError("synthetic acceptance stage failure")

    wrapped = sic.wrap_with_io_capture(
        execute=_execute,
        stage_key="acceptance_decision",
    )

    with pytest.raises(RuntimeError):
        wrapped(_Ctx(), {"x": 1})

    failures = sic.consume_capture_failures()
    assert any(
        f["stage_key"] == "acceptance_decision"
        and f["error_class"] == "RuntimeError"
        for f in failures
    ), failures
