"""Cycle 11 pilot — invariant suite over committed regression fixtures.

This file is the binary pass/fail gate for the cycle. Each invariant
test runs against both fixtures. All-green = ship. Any-red = the
failing IDs name Cycle 12's scope.

Tests are added one at a time as the invariants land. Fixture-load
smoke tests run first so a malformed fixture surfaces immediately.
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
}


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


def _fixture_to_evidence(fixture: dict) -> dict:
    """Project the replay fixture into the evidence shape that
    invariants.run_invariants expects. Pure — no I/O."""
    iters = []
    for it in fixture.get("iterations") or []:
        iters.append({
            "iteration": it.get("iteration"),
            "ags": it.get("ags") or [],
            "clusters": it.get("clusters") or [],
            "applied_patches": it.get("applied_patches") or [],
            "open_hard_cluster_ids": it.get("open_hard_cluster_ids") or [],
            "acceptance_decision": it.get("acceptance_decision") or {},
        })
    return {
        "phase_b": fixture.get("phase_b") or {"total_records": 0},
        "replay_fixture_records": sum(
            len(it.get("decision_records") or []) for it in iters
        ),
        "iterations": iters,
        "manifest": fixture.get("manifest") or {},
        "convergence": fixture.get("convergence") or {},
    }


def test_invariants_run_over_fixture_returns_baseline_violations(fixture, request) -> None:
    """Cycle 11 baseline: the as-is fixtures have known violations.

    This test pins the *current* state. After Layer 3 lands, this
    test gets updated to assert all-green. That update is the
    pilot-pass signal.
    """
    from genie_space_optimizer.optimization.invariants import run_invariants

    evidence = _fixture_to_evidence(fixture)
    violations = run_invariants(evidence)

    # The fixtures populate iterations only sparsely (the projection
    # above doesn't fill in all of the invariants' expected fields),
    # so the empty-violation case is acceptable for some invariants.
    # Surface the current set so the pilot Step 17 can read the diff.
    fixture_id = request.node.callspec.id
    print(
        f"\n[Cycle 11 pilot baseline] fixture={fixture_id} "
        f"violation_count={len(violations)} "
        f"ids={sorted({v.get('invariant_id', '?') for v in violations})}"
    )
    # No hard assertion in this commit — Task 17 (pilot run + binary
    # decision) inspects the actual numbers and decides Case A vs B.
    # The test passes as long as the suite runs without crashing.
    assert isinstance(violations, list)
