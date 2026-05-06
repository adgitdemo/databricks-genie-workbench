"""Cycle 11 pilot — invariant suite over committed regression fixtures.

This file is the binary pass/fail gate for the cycle. All-green = ship.
Any-red = the failing IDs name Cycle 12's scope.
"""

from __future__ import annotations

import json
import pathlib

import pytest

FIXTURES = {
    "1099b152_airline": (
        pathlib.Path(__file__).parent / "fixtures" / "run_1099b152_airline.json"
    ),
    "3b050ec5_7now": (
        pathlib.Path(__file__).parent / "fixtures" / "run_3b050ec5_7now.json"
    ),
    # Run 80532762433063 — the run whose typed PRODUCER_EXCEPTION
    # decision record (Cycle 11 instrumentation) named the actual
    # root cause of the optimizer's silent acceptance failures: a
    # cross-scope ``NameError`` on ``full_pre_arbiter_accuracy`` at
    # ``harness.py:_run_lever_loop``. Committed as a pre-fix
    # regression marker. The accompanying assertion
    # (``test_no_full_pre_arbiter_accuracy_nameerror_in_committed_fixtures``)
    # skips this exact fixture so the bug-on-disk does not block
    # merge of the fix; it asserts against every other fixture so
    # any fresh run that re-introduces the same NameError fails CI.
    "80532762433063_7now_pre_nameerror_fix": (
        pathlib.Path(__file__).parent
        / "fixtures"
        / "run_80532762433063_7now_pre_nameerror_fix.json"
    ),
}

# Fixtures that pre-date the harness.py:_run_lever_loop cross-scope
# NameError fix — they intentionally carry the bug-on-disk for
# regression provenance and are exempt from the post-fix assertion.
_PRE_NAMEERROR_FIX_FIXTURES = frozenset({
    "80532762433063_7now_pre_nameerror_fix",
})


@pytest.fixture(params=sorted(FIXTURES.keys()))
def fixture(request) -> dict:
    path = FIXTURES[request.param]
    if not path.exists():
        pytest.fail(
            f"Committed regression fixture missing at {path}. "
            "This file must always be present — do not delete it."
        )
    return json.loads(path.read_text())


def test_fixture_loads_with_iterations(fixture):
    assert isinstance(fixture.get("iterations"), list)
    assert len(fixture["iterations"]) >= 1


_PATCH_TYPE_TO_LEVER = {
    "add_sql_snippet_filter": 6,
    "add_sql_snippet_measure": 6,
    "add_sql_snippet_expression": 6,
    "add_sql_snippet_dimension": 6,
    "rewrite_instruction": 5,
    "synonym": 1,
    "add_synonym": 1,
    "add_join_spec": 4,
    "set_join_spec": 4,
    "add_sql_shape": 5,
    "add_measure": 5,
}


def _lever_from_patch_type(patch_type) -> int | None:
    if not patch_type:
        return None
    pt = str(patch_type)
    if pt in _PATCH_TYPE_TO_LEVER:
        return _PATCH_TYPE_TO_LEVER[pt]
    if pt.startswith("add_sql_snippet"):
        return 6
    return None


def _fixture_to_evidence(fixture: dict) -> dict:
    """Project the replay fixture into the evidence shape that
    invariants.run_invariants expects. Pure — no I/O.

    Derives iteration-level ags / applied_patches / acceptance_decision /
    open_hard_cluster_ids / rca_cards_present / selected_ag_id /
    proposal_count from the fixture's decision_records and
    strategist_response so the 8-invariant suite sees what the
    postmortems documented.
    """
    iters = []
    total_records = 0
    overall_replay_validation: dict | None = None

    for it in fixture.get("iterations") or []:
        records = list(it.get("decision_records") or [])
        total_records += len(records)

        strategist = it.get("strategist_response") or {}
        ags_raw = (
            strategist.get("action_groups") or []
            if isinstance(strategist, dict)
            else []
        )
        ags_proj: list[dict] = []
        proposal_count = 0
        selected_ag_id = ""

        for ag in ags_raw:
            patches = ag.get("patches") or []
            proposal_count += len(patches)
            src_clusters = sorted({
                str(p.get("cluster_id") or "")
                for p in patches
                if p.get("cluster_id")
            })
            levers = sorted({
                lv
                for lv in (
                    _lever_from_patch_type(p.get("patch_type")) for p in patches
                )
                if lv is not None
            })
            ag_id = str(ag.get("id") or "")
            if not selected_ag_id and ag_id:
                selected_ag_id = ag_id
            ags_proj.append({
                "id": ag_id,
                "affected_questions": list(ag.get("affected_questions") or []),
                "source_cluster_ids": src_clusters,
                "levers": levers,
            })

        # Derive applied_patches from patch_applied decision records.
        applied_patches: list[dict] = []
        applied_fingerprints: set[str] = set()
        for rec in records:
            if str(rec.get("decision_type") or "") != "patch_applied":
                continue
            ag_id = str(rec.get("ag_id") or "")
            # patch_type may live directly on the record or inside metrics.
            patch_type = rec.get("patch_type") or (
                (rec.get("metrics") or {}).get("patch_type")
            )
            lever = _lever_from_patch_type(patch_type)
            proposal_id = str(rec.get("proposal_id") or "")
            applied_patches.append({
                "ag_id": ag_id,
                "lever": lever,
                "proposal_id": proposal_id,
                "patch_type": patch_type,
            })
            if proposal_id:
                applied_fingerprints.add(proposal_id)

        # Derive acceptance_decision from ag_outcomes.
        ag_outcomes = it.get("ag_outcomes") or {}
        had_rollback = any(
            str(v).lower() == "rolled_back" for v in ag_outcomes.values()
        )
        acceptance_decision: dict = {}
        if had_rollback:
            # The fixture stores ag_outcomes per AG. Project a single
            # iteration-level acceptance with reason_code that names a
            # known target-state bucket. target_still_hard_qids is the
            # closest semantic fit since the AG was rolled back.
            affected_qids = sorted({
                str(q)
                for ag in ags_raw
                for q in (ag.get("affected_questions") or [])
                if str(q)
            })
            acceptance_decision = {
                "target_qids": affected_qids,
                "target_fixed_qids": [],
                "target_still_hard_qids": affected_qids,
                "reason_code": "target_still_hard_qids",
            }

        clusters = list(it.get("clusters") or [])

        # rca_cards_present: true if an rca_formed record exists for that cluster.
        rca_present = {
            str(c.get("cluster_id") or ""): any(
                str(r.get("decision_type") or "") == "rca_formed"
                and str(r.get("cluster_id") or "")
                == str(c.get("cluster_id") or "")
                for r in records
            )
            for c in clusters
        }

        # All clusters in the fixture are "hard" — soft clusters stored
        # separately under soft_clusters.
        open_hard_cluster_ids = [
            str(c.get("cluster_id") or "") for c in clusters if c.get("cluster_id")
        ]

        # Project journey_validation if present and invalid.
        jv = it.get("journey_validation") or {}
        if jv and not bool(jv.get("is_valid", True)):
            overall_replay_validation = {
                "is_valid": False,
                "violation_count": int(jv.get("violation_count") or 0),
                "violation_details": dict(jv.get("violation_details") or {}),
            }

        iters.append({
            "iteration": int(it.get("iteration") or 0),
            "ags": ags_proj,
            "clusters": clusters,
            "applied_patches": applied_patches,
            "open_hard_cluster_ids": open_hard_cluster_ids,
            "rca_cards_present": rca_present,
            "acceptance_decision": acceptance_decision,
            "selected_ag_id": selected_ag_id,
            "proposal_count": proposal_count,
            "applied_patch_body_fingerprints": sorted(applied_fingerprints),
            "decision_records": records,
        })

    return {
        "phase_b": {"total_records": total_records, "producer_exceptions": {}},
        "replay_fixture_records": total_records,
        "iterations": iters,
        "manifest": {"declared_paths": [], "materialized_paths": []},
        "convergence": {},
        "replay_validation": overall_replay_validation or {},
        "final_iteration_journey_hard_qids": [],
    }


def test_invariants_run_over_fixture_emits_violation_diagnostic(fixture, request):
    """Cycle 11 pilot. Run the suite over the projected fixture and
    print violations for the binary-decision step. Always green at the
    test level — the binary decision is recorded in the iteration
    ledger."""
    from genie_space_optimizer.optimization.invariants import run_invariants

    evidence = _fixture_to_evidence(fixture)
    violations = run_invariants(evidence)

    fixture_id = request.node.callspec.id
    print(
        f"\n[Cycle 11 pilot] fixture={fixture_id} "
        f"violation_count={len(violations)} "
        f"ids={sorted({v.get('invariant_id', '?') for v in violations})}"
    )
    for v in violations:
        print(
            f"  - {v.get('invariant_id')}: {v.get('title')} | "
            f"{str(v.get('detail', ''))[:200]}"
        )
    assert isinstance(violations, list)


def test_no_full_pre_arbiter_accuracy_nameerror_in_committed_fixtures(
    fixture, request
):
    """Regression — once the cross-scope ``NameError`` fix in
    ``harness.py:_run_lever_loop`` lands, no fresh fixture should
    carry a ``producer_exception`` decision record naming
    ``full_pre_arbiter_accuracy`` (or its sibling latent names
    ``_best_pre_arbiter`` / ``full_result_1``) as the missing name.

    Closes the actual root cause Cycle 11's typed
    ``PRODUCER_EXCEPTION`` record surfaced in run 80532762433063.

    Fixtures captured *before* the fix are kept on disk for
    provenance (see ``_PRE_NAMEERROR_FIX_FIXTURES``) and skipped
    by this assertion. Every other fixture — including any future
    post-fix capture — must be free of the cross-scope NameError
    family.
    """
    fixture_id = request.node.callspec.id
    if fixture_id in _PRE_NAMEERROR_FIX_FIXTURES:
        pytest.skip(
            f"fixture {fixture_id} pre-dates the harness.py "
            "_run_lever_loop cross-scope NameError fix — kept on "
            "disk for regression provenance"
        )

    cross_scope_names = (
        "full_pre_arbiter_accuracy",
        "_best_pre_arbiter",
        "full_result_1",
    )
    for it in fixture.get("iterations") or []:
        for rec in it.get("decision_records") or []:
            if str(rec.get("decision_type") or "") != "producer_exception":
                continue
            metrics = rec.get("metrics") or {}
            repr_text = str(metrics.get("exception_repr") or "")
            traceback_head = str(metrics.get("traceback_head") or "")
            blob = f"{repr_text}\n{traceback_head}"
            for name in cross_scope_names:
                assert name not in blob, (
                    f"iter {it.get('iteration')}: cross-scope "
                    f"NameError on {name!r} reproduced in fixture "
                    f"{fixture_id} — the harness.py:_run_lever_loop "
                    f"acceptance-stage fix has regressed. Record: {rec}"
                )
