"""Pin the harness's iteration pre-stamp / finalise contract.

Run ``1099b152-8655-4f1e-ab43-1240a9400280`` rolled back twice via the
content-regression continue at ``harness.py:19749``. Because
``_iter_traces[N]`` was only populated at the end-of-iteration body, the
rendered ``operator_transcript.md`` was 567 bytes — only the run-overview
header. The pre-stamp ensures every iteration that started has at least
a stub trace to render, and the finalise overwrite carries the rich data
when it is available.
"""

from __future__ import annotations

from typing import Any

from genie_space_optimizer.optimization.harness import (
    _stamp_iteration_stub,
)
from genie_space_optimizer.optimization.rca_decision_trace import (
    OptimizationTrace,
)


def test_stamp_iteration_stub_populates_empty_trace_and_in_progress_summary() -> None:
    iter_traces: dict[int, Any] = {}
    iter_summaries: dict[int, dict[str, Any]] = {}
    _stamp_iteration_stub(
        iter_traces=iter_traces,
        iter_summaries=iter_summaries,
        iteration=1,
    )
    assert isinstance(iter_traces[1], OptimizationTrace)
    assert iter_traces[1].journey_events == ()
    assert iter_traces[1].decision_records == ()
    assert iter_summaries[1]["iteration"] == 1
    assert iter_summaries[1]["exit_path"] == "in_progress"
    assert iter_summaries[1]["decision_record_count"] == 0


def test_stamp_iteration_stub_is_idempotent_when_called_twice() -> None:
    """Defensive: if a future caller stamps twice, the second call must
    not raise and must leave the dict in the same shape (the rich finalise
    overwrite is the only intended re-write path)."""
    iter_traces: dict[int, Any] = {}
    iter_summaries: dict[int, dict[str, Any]] = {}
    _stamp_iteration_stub(
        iter_traces=iter_traces,
        iter_summaries=iter_summaries,
        iteration=3,
    )
    _stamp_iteration_stub(
        iter_traces=iter_traces,
        iter_summaries=iter_summaries,
        iteration=3,
    )
    assert iter_summaries[3]["exit_path"] == "in_progress"
