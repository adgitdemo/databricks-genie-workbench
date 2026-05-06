"""Pre-step Cycle 11: contract tests for the harness invariant runner.

These pin the runner to call ``project_iter_evidence`` instead of
the empty literal.
"""

from __future__ import annotations

import inspect


def test_run_iteration_invariants_imports_project_iter_evidence() -> None:
    from genie_space_optimizer.optimization import harness as _h

    src = inspect.getsource(_h._run_iteration_invariants_and_append_records)
    assert "project_iter_evidence" in src, (
        "Cycle 11 Task 12 wrapper must call project_iter_evidence; "
        "current source still uses the empty literal."
    )


def test_run_iteration_invariants_passes_run_id_through() -> None:
    from genie_space_optimizer.optimization import harness as _h

    sig = inspect.signature(_h._run_iteration_invariants_and_append_records)
    assert "run_id" in sig.parameters
    assert "current_iter_inputs" in sig.parameters
    assert "iteration" in sig.parameters
    assert "iter_producer_exceptions" in sig.parameters
    assert "prior_iter_evidence" in sig.parameters, (
        "Cycle 11 Task 12 wrapper must accept prior_iter_evidence so "
        "I4 (no silent retry) sees prev+curr in one evidence dict."
    )


def test_run_iteration_invariants_calls_run_invariants_on_projected_evidence(
    monkeypatch,
) -> None:
    from genie_space_optimizer.optimization import harness as _h

    captured: list[dict] = []

    def _fake_run_invariants(evidence):
        captured.append(dict(evidence or {}))
        return []

    monkeypatch.setattr(
        "genie_space_optimizer.optimization.invariants.run_invariants",
        _fake_run_invariants,
    )

    iter_inputs = {
        "clusters": [{"cluster_id": "H1", "recommended_levers": [1]}],
        "strategist_response": {
            "action_groups": [{
                "id": "AG1",
                "Levers": [1],
                "source_cluster_ids": ["H1"],
            }],
        },
        "decision_records": [],
    }
    _h._run_iteration_invariants_and_append_records(
        run_id="r1",
        iteration=3,
        current_iter_inputs=iter_inputs,
        iter_producer_exceptions={},
        prior_iter_evidence=None,
    )

    assert captured, "run_invariants was not invoked with projected evidence"
    iters = captured[-1].get("iterations") or []
    assert len(iters) == 1
    assert int(iters[0]["iteration"]) == 3
    assert iters[0]["ags"][0]["id"] == "AG1"
