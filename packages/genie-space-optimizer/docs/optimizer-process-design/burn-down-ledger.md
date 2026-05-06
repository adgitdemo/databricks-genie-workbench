# Burn-down ledger


## Pre-step Cycle 11 invariant projection — deferred items

- Project `manifest.declared_paths` / `manifest.materialized_paths` for I6 at run-end (Phase H artifact-completeness work).
- Project `replay_validation` for I5 at run-end (replay validity Phase A work).
- Project `final_iteration_journey_hard_qids` for I8 at run-end (journey ledger Phase A work).
- Strict mode default: keep `loop_invariants_strict()` False until two consecutive replays produce zero unexpected violations.
