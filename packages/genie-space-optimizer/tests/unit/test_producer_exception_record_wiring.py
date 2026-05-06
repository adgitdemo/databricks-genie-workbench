"""Cycle 11 — wiring test: producer_exception_record is appended to
``decision_records`` whenever a producer try/except increments a
counter.

Direct unit-test of the ``_phase_b_emit_ag_outcome_record`` closure
shape: we monkey-patch ``ag_outcome_decision_record`` to raise and
assert (a) the counter increments AND (b) a typed
``PRODUCER_EXCEPTION`` record lands in the iteration's
``decision_records`` list.

We exercise the closure shape rather than the full harness so this
test stays fast and self-contained.
"""

from __future__ import annotations

import pytest


def test_phase_b_emit_ag_outcome_appends_typed_exception_record(monkeypatch) -> None:
    monkeypatch.delenv("GSO_PHASE_B_PRODUCER_TYPED_EXCEPTIONS", raising=False)
    monkeypatch.delenv("GSO_DECISION_EMITTER_STRICT", raising=False)

    # Force the inner producer to raise.
    from genie_space_optimizer.optimization import decision_emitters as _de

    def _raise(**kwargs):
        raise RuntimeError("synthetic ag_outcome failure")

    monkeypatch.setattr(_de, "ag_outcome_decision_record", _raise)

    decision_records: list[dict] = []
    iter_exc: dict[str, int] = {"ag_outcome": 0}
    run_exc: dict[str, int] = {}

    def _emit_ag_outcome(ag, outcome):
        # Mirror the closure body in harness.py:14176-14205.
        try:
            rec = _de.ag_outcome_decision_record(
                run_id="run-1", iteration=1, ag=ag, outcome=outcome,
                source_clusters_by_id={}, rca_id_by_cluster={},
            )
            if rec is not None:
                decision_records.append(rec.to_dict())
        except Exception as exc:
            from genie_space_optimizer.common.config import (
                phase_b_producer_typed_exceptions_enabled,
            )
            if phase_b_producer_typed_exceptions_enabled():
                rec = _de.producer_exception_record(
                    run_id="run-1", iteration=1,
                    producer="ag_outcome",
                    ag_id=str(ag.get("id") or ""),
                    exception=exc,
                )
                decision_records.append(rec.to_dict())
            iter_exc["ag_outcome"] += 1
            run_exc["ag_outcome"] = run_exc.get("ag_outcome", 0) + 1

    _emit_ag_outcome({"id": "AG_DECOMPOSED_H004"}, "rolled_back")

    assert iter_exc["ag_outcome"] == 1
    assert run_exc["ag_outcome"] == 1
    assert len(decision_records) == 1
    rec = decision_records[0]
    assert rec["decision_type"] == "producer_exception"
    assert rec["ag_id"] == "AG_DECOMPOSED_H004"
    assert rec["metrics"]["producer"] == "ag_outcome"
    assert rec["metrics"]["exception_class"] == "RuntimeError"


def test_phase_b_emit_ag_outcome_skips_typed_record_when_flag_off(monkeypatch) -> None:
    monkeypatch.setenv("GSO_PHASE_B_PRODUCER_TYPED_EXCEPTIONS", "0")
    from genie_space_optimizer.optimization import decision_emitters as _de

    def _raise(**kwargs):
        raise RuntimeError("synthetic ag_outcome failure")

    monkeypatch.setattr(_de, "ag_outcome_decision_record", _raise)

    decision_records: list[dict] = []
    iter_exc: dict[str, int] = {"ag_outcome": 0}

    def _emit_ag_outcome(ag, outcome):
        try:
            _de.ag_outcome_decision_record(
                run_id="r", iteration=1, ag=ag, outcome=outcome,
                source_clusters_by_id={}, rca_id_by_cluster={},
            )
        except Exception as exc:
            from genie_space_optimizer.common.config import (
                phase_b_producer_typed_exceptions_enabled,
            )
            if phase_b_producer_typed_exceptions_enabled():
                rec = _de.producer_exception_record(
                    run_id="r", iteration=1, producer="ag_outcome",
                    ag_id=str(ag.get("id") or ""), exception=exc,
                )
                decision_records.append(rec.to_dict())
            iter_exc["ag_outcome"] += 1

    _emit_ag_outcome({"id": "AG_X"}, "rolled_back")
    assert iter_exc["ag_outcome"] == 1
    assert decision_records == []  # flag off → no typed record
