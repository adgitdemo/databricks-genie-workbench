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


def _ag_levers(ag: Mapping[str, Any]) -> set[int]:
    """Best-effort: read AG levers from the standard fields used by
    the strategist + decomposer. Falls back to keys of
    ``lever_directives``."""
    levers = ag.get("levers") or ag.get("Levers")
    if levers:
        return {int(x) for x in levers if str(x).strip()}
    directives = ag.get("lever_directives") or {}
    return {int(k) for k in directives.keys() if str(k).strip().isdigit()}


def check_i2_lever_coherence(evidence: Mapping[str, Any]) -> list[dict]:
    """I2 — for each iteration, every applied patch's lever must be
    within its AG's declared lever set, and the AG's lever set must
    be a superset of every source cluster's ``recommended_levers``.
    """
    violations: list[dict] = []
    for it in evidence.get("iterations") or []:
        clusters_by_id = {
            str(c.get("cluster_id") or ""): c
            for c in (it.get("clusters") or [])
        }
        for ag in it.get("ags") or []:
            ag_id = str(ag.get("id") or "")
            ag_levers = _ag_levers(ag)
            for cid in ag.get("source_cluster_ids") or []:
                cluster = clusters_by_id.get(str(cid)) or {}
                rec = {
                    int(x) for x in (cluster.get("recommended_levers") or [])
                    if str(x).strip()
                }
                missing = rec - ag_levers
                if missing:
                    violations.append(_violation(
                        invariant_id="I2",
                        title="ag_levers_missing_recommended",
                        detail=(
                            f"AG {ag_id} levers={sorted(ag_levers)} missing "
                            f"recommended {sorted(missing)} from cluster {cid}"
                        ),
                        iteration=int(it.get("iteration") or 0),
                        ag_id=ag_id,
                        cluster_id=str(cid),
                        ag_levers=sorted(ag_levers),
                        missing_levers=sorted(missing),
                    ))
        applied_by_ag: dict[str, set[int]] = {}
        for patch in it.get("applied_patches") or []:
            ag_id = str(patch.get("ag_id") or "")
            try:
                lever = int(patch.get("lever"))
            except (TypeError, ValueError):
                continue
            applied_by_ag.setdefault(ag_id, set()).add(lever)
        ag_index = {str(a.get("id") or ""): a for a in it.get("ags") or []}
        for ag_id, levers_used in applied_by_ag.items():
            ag_levers = _ag_levers(ag_index.get(ag_id) or {})
            outside = levers_used - ag_levers
            if outside:
                violations.append(_violation(
                    invariant_id="I2",
                    title="patch_lever_outside_ag",
                    detail=(
                        f"AG {ag_id} applied lever(s) {sorted(outside)} "
                        f"not in declared {sorted(ag_levers)}"
                    ),
                    iteration=int(it.get("iteration") or 0),
                    ag_id=ag_id,
                    outside_levers=sorted(outside),
                    ag_levers=sorted(ag_levers),
                ))
    return violations


_TARGET_BUCKET_KEYS = (
    "target_fixed_qids",
    "target_still_hard_qids",
    "target_hard_to_soft_qids",
    "target_hard_to_pass_with_judge_debt_qids",
    "target_all_judge_fixed_qids",
    "target_unchanged_qids",
)


def check_i3_acceptance_buckets(evidence: Mapping[str, Any]) -> list[dict]:
    """I3 — target-state buckets partition target_qids; rollback
    reason names a bucket. Closes 7NOW (target_fixed=(), still_hard=(),
    reason=target_qids_not_improved) inconsistency."""
    violations: list[dict] = []
    for it in evidence.get("iterations") or []:
        ad = dict(it.get("acceptance_decision") or {})
        if not ad:
            continue
        target_qids = {str(q) for q in (ad.get("target_qids") or []) if str(q)}
        if not target_qids:
            continue
        bucket_qids: dict[str, set[str]] = {}
        union: set[str] = set()
        seen_twice: set[str] = set()
        for key in _TARGET_BUCKET_KEYS:
            qids = {str(q) for q in (ad.get(key) or []) if str(q)}
            seen_twice.update(qids & union)
            union |= qids
            bucket_qids[key] = qids
        missing = target_qids - union
        if missing:
            violations.append(_violation(
                invariant_id="I3",
                title="target_qids_missing_from_all_buckets",
                detail=(
                    f"target_qids={sorted(target_qids)} not covered by any "
                    f"bucket; missing={sorted(missing)}"
                ),
                iteration=int(it.get("iteration") or 0),
                missing_qids=sorted(missing),
            ))
        if seen_twice:
            violations.append(_violation(
                invariant_id="I3",
                title="target_qids_double_counted_in_buckets",
                detail=f"qids in two buckets: {sorted(seen_twice)}",
                iteration=int(it.get("iteration") or 0),
                double_counted=sorted(seen_twice),
            ))
        reason = str(ad.get("reason_code") or "")
        if reason and reason not in _TARGET_BUCKET_KEYS:
            violations.append(_violation(
                invariant_id="I3",
                title="rollback_reason_does_not_name_a_bucket",
                detail=f"reason_code={reason!r} is not one of {_TARGET_BUCKET_KEYS}",
                iteration=int(it.get("iteration") or 0),
                reason_code=reason,
            ))
    return violations


def check_i4_no_silent_retry(evidence: Mapping[str, Any]) -> list[dict]:
    """I4 — no two consecutive iterations may select the same AG with
    the same applied-patch body-fingerprint set OR with empty proposals.
    Closes airline iter-1/iter-2 H004 retread and 7NOW iter-2..5 spin."""
    violations: list[dict] = []
    iters = list(evidence.get("iterations") or [])
    for i in range(1, len(iters)):
        prev = iters[i - 1]
        curr = iters[i]
        prev_ag = str(prev.get("selected_ag_id") or "")
        curr_ag = str(curr.get("selected_ag_id") or "")
        if not prev_ag or prev_ag != curr_ag:
            continue
        prev_count = int(prev.get("proposal_count") or 0)
        curr_count = int(curr.get("proposal_count") or 0)
        if prev_count == 0 and curr_count == 0:
            violations.append(_violation(
                invariant_id="I4",
                title="consecutive_empty_proposals_same_ag",
                detail=(
                    f"AG {curr_ag} produced 0 proposals in iterations "
                    f"{prev.get('iteration')} and {curr.get('iteration')}"
                ),
                iteration=int(curr.get("iteration") or 0),
                ag_id=curr_ag,
            ))
            continue
        prev_acc = dict(prev.get("acceptance_decision") or {})
        prev_was_rollback = (
            str(prev_acc.get("reason_code") or "")
            != "target_fixed_qids"  # any non-fixed reason ⇒ rollback
            and prev_acc != {}
        )
        if not prev_was_rollback:
            continue
        prev_fp = sorted(
            str(f) for f in (prev.get("applied_patch_body_fingerprints") or [])
        )
        curr_fp = sorted(
            str(f) for f in (curr.get("applied_patch_body_fingerprints") or [])
        )
        if prev_fp and prev_fp == curr_fp:
            violations.append(_violation(
                invariant_id="I4",
                title="same_body_fingerprints_after_rollback",
                detail=(
                    f"AG {curr_ag} re-applied identical patch bodies "
                    f"{prev_fp} after a rollback"
                ),
                iteration=int(curr.get("iteration") or 0),
                ag_id=curr_ag,
                fingerprints=prev_fp,
            ))
    return violations


# Stubs for I5..I8 — populated in subsequent tasks. The aggregator
# tolerates missing checks so each can land in its own commit.

def run_invariants(evidence: Mapping[str, Any]) -> list[dict]:
    """Aggregate every implemented invariant check; return all
    violations. Empty list = green pilot."""
    violations: list[dict] = []
    for check in (
        check_i1_phase_b_records_present,
        check_i2_lever_coherence,
        check_i3_acceptance_buckets,
        check_i4_no_silent_retry,
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
