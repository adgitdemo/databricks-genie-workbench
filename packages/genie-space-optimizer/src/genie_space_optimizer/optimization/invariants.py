"""Cycle 11 — Loop invariants over existing markers / decision records.

Each ``check_iN_*`` function is pure: takes a single ``evidence``
dict (markers + decision records + replay-fixture metadata) and
returns a list of ``invariant_violation`` dicts. Empty list = green.

The aggregator ``run_invariants`` calls every implemented check and
returns the combined violation list. CI/replay treat any non-empty
list as a hard failure; production records each violation as an
``INVARIANT_VIOLATION`` decision record and continues (gated by
``loop_invariants_strict``).

The invariants are intentionally read-only over evidence the
harness already produces. No new emitters are required beyond the
``invariant_violation_record`` helper in ``decision_emitters.py``.

Invariant IDs:
  I1 — phase_b.total_records >= replay_fixture.records
  I2 — applied_patch.lever ⊆ ag.Levers ⊇ cluster.recommended_levers
  I3 — acceptance buckets partition target_qids; rollback reason names
       a bucket
  I4 — no two consecutive iterations select the same AG with the same
       applied-patch body-fingerprint set or with Proposals(0 total)
  I5 — replay validity: zero illegal trunk transitions
  I6 — phase_h declared paths == materialized paths
  I7 — every open hard cluster reaching AG-emit has a fit RCA card or
       a cluster_blocked_no_rca typed record
  I8 — plateau decision currently_failing input matches journey-ledger
       hard-cluster set after rollback
"""

from __future__ import annotations

from typing import Any, Mapping


def _violation(
    *,
    invariant_id: str,
    title: str,
    detail: str,
    **extra: Any,
) -> dict:
    out = {
        "invariant_id": str(invariant_id),
        "title": str(title),
        "detail": str(detail),
    }
    out.update({k: v for k, v in extra.items()})
    return out


def check_i1_phase_b_records_present(evidence: Mapping[str, Any]) -> list[dict]:
    """I1 — Phase B's ``total_records`` must be at least the replay
    fixture's record count. Closes the airline / 7NOW silent-mute
    case where producer exceptions caused
    ``phase_b.total_records=0`` while the fixture itself contained
    decision records.
    """
    phase_b = dict(evidence.get("phase_b") or {})
    total = int(phase_b.get("total_records") or 0)
    replay = int(evidence.get("replay_fixture_records") or 0)
    if total < replay:
        return [_violation(
            invariant_id="I1",
            title="phase_b.total_records below replay_fixture.records",
            detail=(
                f"phase_b.total_records={total} < "
                f"replay_fixture.records={replay}"
            ),
            phase_b_total_records=total,
            replay_fixture_records=replay,
            producer_exceptions=dict(phase_b.get("producer_exceptions") or {}),
        )]
    return []


# Stubs for I2..I8 — populated in subsequent tasks. The aggregator
# tolerates missing checks so each can land in its own commit.

def run_invariants(evidence: Mapping[str, Any]) -> list[dict]:
    """Aggregate every implemented invariant check; return all
    violations. Empty list = green pilot."""
    violations: list[dict] = []
    for check in (
        check_i1_phase_b_records_present,
    ):
        try:
            violations.extend(check(evidence))
        except Exception as exc:  # invariant bugs must not crash runs
            violations.append(_violation(
                invariant_id="I_CHECK_FAILED",
                title=f"invariant check {check.__name__} raised",
                detail=repr(exc)[:512],
            ))
    return violations
