"""Unit tests for the typed PRODUCER_EXCEPTION decision-record emitter.

Closes the airline / 7NOW silent-mute defect: today every producer
try/except in harness.py only increments a counter and debug-logs;
the exception class, message, and traceback head are nowhere in the
postmortem. This emitter stamps a typed DecisionRecord so the Phase B
trace and invariant suite can see the failure.
"""

from __future__ import annotations


def test_producer_exception_record_carries_class_repr_and_traceback_head() -> None:
    from genie_space_optimizer.optimization.decision_emitters import (
        producer_exception_record,
    )
    from genie_space_optimizer.optimization.rca_decision_trace import (
        DecisionOutcome,
        DecisionType,
        ReasonCode,
    )

    try:
        raise ValueError("synthetic failure for ag_outcome producer")
    except ValueError as exc:
        record = producer_exception_record(
            run_id="run-abc",
            iteration=1,
            producer="ag_outcome",
            ag_id="AG_DECOMPOSED_H004",
            exception=exc,
        )

    assert record is not None
    assert record.decision_type == DecisionType.PRODUCER_EXCEPTION
    assert record.outcome == DecisionOutcome.FAILED
    assert record.reason_code == ReasonCode.PRODUCER_EXCEPTION
    assert record.run_id == "run-abc"
    assert record.iteration == 1
    assert record.ag_id == "AG_DECOMPOSED_H004"
    metrics = dict(record.metrics or {})
    assert metrics.get("producer") == "ag_outcome"
    assert metrics.get("exception_class") == "ValueError"
    repr_text = str(metrics.get("exception_repr") or "")
    assert "synthetic failure for ag_outcome producer" in repr_text
    tb_head = str(metrics.get("traceback_head") or "")
    assert "test_producer_exception_record" in tb_head
    assert len(repr_text) <= 512
    assert len(tb_head) <= 2048


def test_producer_exception_record_without_ag_id_still_emits() -> None:
    from genie_space_optimizer.optimization.decision_emitters import (
        producer_exception_record,
    )
    from genie_space_optimizer.optimization.rca_decision_trace import (
        DecisionType,
    )

    try:
        raise RuntimeError("phase b producer dropped")
    except RuntimeError as exc:
        record = producer_exception_record(
            run_id="run-xyz",
            iteration=2,
            producer="rca_formed",
            ag_id=None,
            exception=exc,
        )
    assert record is not None
    assert record.decision_type == DecisionType.PRODUCER_EXCEPTION
    assert record.ag_id == ""


def test_phase_b_producer_typed_exceptions_flag_default_on(monkeypatch) -> None:
    monkeypatch.delenv("GSO_PHASE_B_PRODUCER_TYPED_EXCEPTIONS", raising=False)
    from genie_space_optimizer.common.config import (
        phase_b_producer_typed_exceptions_enabled,
    )
    assert phase_b_producer_typed_exceptions_enabled() is True


def test_phase_b_producer_typed_exceptions_flag_override_off(monkeypatch) -> None:
    monkeypatch.setenv("GSO_PHASE_B_PRODUCER_TYPED_EXCEPTIONS", "0")
    from genie_space_optimizer.common.config import (
        phase_b_producer_typed_exceptions_enabled,
    )
    assert phase_b_producer_typed_exceptions_enabled() is False
