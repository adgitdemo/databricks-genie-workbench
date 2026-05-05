from __future__ import annotations


def test_harness_marks_no_applied_bundle_as_dead_on_arrival() -> None:
    """Asserts the dead-on-arrival markers appear in the skip-eval
    branch (after ``_apply_skip = ...``) without using a fixed
    character window — the harness has grown such that these markers
    sit ~5000 chars after the skip entry, so any hard window risks
    drifting again.
    """
    import inspect

    from genie_space_optimizer.optimization import harness

    source = inspect.getsource(harness._run_lever_loop)
    skip_idx = source.index("_apply_skip = _should_skip_eval_for_patch_bundle(")

    # These must appear AFTER the skip-eval branch entry.
    for needle in (
        "deterministic_no_applied_patches",
        "all_selected_patches_dropped_by_applier",
        "pending_action_groups = []",
        "pending_strategy = None",
    ):
        n_idx = source.find(needle, skip_idx)
        assert n_idx > skip_idx, (
            f"{needle!r} must appear AFTER the skip-eval branch entry"
        )

    # These can appear anywhere in the function (declared outside the branch).
    assert "_dead_on_arrival_patch_signatures" in source
    assert "_dead_on_arrival_ag_ids" in source


def test_harness_blocks_retry_of_same_dead_patch_signature() -> None:
    import inspect

    from genie_space_optimizer.optimization import harness

    source = inspect.getsource(harness._run_lever_loop)
    assert "_selected_patch_signature = tuple(sorted(" in source
    assert "_selected_patch_signature in _dead_on_arrival_patch_signatures" in source
    assert "Skipping dead-on-arrival AG retry" in source
