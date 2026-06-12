# Burn-down ledger


## Pre-step Cycle 11 invariant projection — deferred items

- Project `manifest.declared_paths` / `manifest.materialized_paths` for I6 at run-end (Phase H artifact-completeness work).
- Project `replay_validation` for I5 at run-end (replay validity Phase A work).
- Project `final_iteration_journey_hard_qids` for I8 at run-end (journey ledger Phase A work).
- Strict mode default: keep `loop_invariants_strict()` False until two consecutive replays produce zero unexpected violations.


## P0 narrow structural fallback (Branch A) — re-pilot exit

Pilot env: `GSO_L6_NARROW_REPLACEMENT_FOR_EXPRESSION=1`,
`GSO_L6_NARROW_REPLACEMENT_PATCH_AWARE=1` (already on).

Replay anchor: `tests/replay/fixtures/run_809960554692716_3b050ec5_pre_p0_fix.json`.

Pilot succeeds iff one of the following is true:

1. The re-pilot transcript contains ≥ 1 `GSO_NARROW_REPLACEMENT_SYNTHESIZED_V1`
   marker AND `target_fixed_qids` for iteration 1 includes
   `7now_delivery_analytics_space_gs_026`.
2. The re-pilot transcript contains ≥ 1 `INVARIANT_VIOLATION` decision
   record (I3 / I4 / I7) that names a specific next fix shape.

Outcome (1) closes the H002 plural-top-N target. Outcome (2) names
the next P0/P1/P2 cycle. A pilot that lands neither is a regression
and the flag flip is reverted.
