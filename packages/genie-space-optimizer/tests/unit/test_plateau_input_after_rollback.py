"""Cycle 11 — after a rollback, the plateau decision's
``currently_failing`` input must come from the journey ledger's
current-baseline hard-cluster set, not from the candidate's eval.
Closes airline `plateau_no_open_failures` with 4 open hard clusters."""

from __future__ import annotations


def test_plateau_currently_failing_after_rollback_uses_journey_ledger() -> None:
    from genie_space_optimizer.optimization.harness import (
        select_plateau_currently_failing,
    )

    candidate_eval_failing = frozenset()  # candidate "fixed" everything
    journey_ledger_hard = frozenset({"q_007", "q_009", "q_013", "q_024"})
    last_acceptance_was_rollback = True

    out = select_plateau_currently_failing(
        candidate_eval_failing=candidate_eval_failing,
        journey_ledger_hard_qids=journey_ledger_hard,
        last_acceptance_was_rollback=last_acceptance_was_rollback,
    )
    assert out == journey_ledger_hard


def test_plateau_currently_failing_uses_eval_when_accepted() -> None:
    from genie_space_optimizer.optimization.harness import (
        select_plateau_currently_failing,
    )
    candidate_eval_failing = frozenset({"q_001"})
    journey_ledger_hard = frozenset({"q_001", "q_002"})
    out = select_plateau_currently_failing(
        candidate_eval_failing=candidate_eval_failing,
        journey_ledger_hard_qids=journey_ledger_hard,
        last_acceptance_was_rollback=False,
    )
    assert out == candidate_eval_failing


def test_plateau_input_uses_journey_after_rollback_flag_default_on(monkeypatch) -> None:
    monkeypatch.delenv("GSO_PLATEAU_INPUT_USES_JOURNEY_AFTER_ROLLBACK", raising=False)
    from genie_space_optimizer.common.config import (
        plateau_input_uses_journey_after_rollback_enabled,
    )
    assert plateau_input_uses_journey_after_rollback_enabled() is True
