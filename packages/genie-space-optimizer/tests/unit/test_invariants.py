"""Cycle 11 — invariant-suite tests. One test per invariant, each
exercises the pure function on synthetic inputs.

I1: phase_b.total_records >= replay_fixture.records
"""

from __future__ import annotations


def test_run_invariants_returns_empty_for_clean_run() -> None:
    from genie_space_optimizer.optimization.invariants import run_invariants

    evidence = {
        "phase_b": {"total_records": 20, "producer_exceptions": {}},
        "replay_fixture_records": 12,
        "iterations": [],
        "manifest": {"declared_paths": [], "materialized_paths": []},
        "convergence": {"reason": "lever_loop_completed"},
    }
    violations = run_invariants(evidence)
    assert violations == []


def test_i1_red_when_phase_b_total_below_replay_records() -> None:
    from genie_space_optimizer.optimization.invariants import check_i1_phase_b_records_present

    evidence = {
        "phase_b": {"total_records": 0, "producer_exceptions": {"ag_outcome": 2}},
        "replay_fixture_records": 12,
    }
    violations = check_i1_phase_b_records_present(evidence)
    assert len(violations) == 1
    v = violations[0]
    assert v["invariant_id"] == "I1"
    assert v["phase_b_total_records"] == 0
    assert v["replay_fixture_records"] == 12


def test_i1_green_when_phase_b_total_meets_replay_records() -> None:
    from genie_space_optimizer.optimization.invariants import check_i1_phase_b_records_present

    evidence = {
        "phase_b": {"total_records": 24, "producer_exceptions": {}},
        "replay_fixture_records": 24,
    }
    assert check_i1_phase_b_records_present(evidence) == []


def test_loop_invariants_flag_default_on(monkeypatch) -> None:
    monkeypatch.delenv("GSO_LOOP_INVARIANTS_ENABLED", raising=False)
    from genie_space_optimizer.common.config import loop_invariants_enabled
    assert loop_invariants_enabled() is True


def test_loop_invariants_strict_flag_default_on(monkeypatch) -> None:
    monkeypatch.delenv("GSO_LOOP_INVARIANTS_STRICT", raising=False)
    from genie_space_optimizer.common.config import loop_invariants_strict
    assert loop_invariants_strict() is True


def test_i2_red_when_patch_lever_outside_ag_levers() -> None:
    from genie_space_optimizer.optimization.invariants import check_i2_lever_coherence

    evidence = {
        "iterations": [{
            "iteration": 1,
            "ags": [{
                "id": "AG1",
                "levers": [1, 5],
                "source_cluster_ids": ["H002"],
            }],
            "applied_patches": [
                {"ag_id": "AG1", "lever": 6, "proposal_id": "P5"},
            ],
            "clusters": [{"cluster_id": "H002", "recommended_levers": [3, 5]}],
        }],
    }
    violations = check_i2_lever_coherence(evidence)
    assert any(v["invariant_id"] == "I2" and "patch_lever_outside_ag" in v["title"]
               for v in violations), violations


def test_i2_red_when_ag_levers_missing_recommended() -> None:
    from genie_space_optimizer.optimization.invariants import check_i2_lever_coherence

    evidence = {
        "iterations": [{
            "iteration": 1,
            "ags": [{
                "id": "AG1",
                "levers": [1, 5],
                "source_cluster_ids": ["H002"],
            }],
            "applied_patches": [
                {"ag_id": "AG1", "lever": 5, "proposal_id": "P1"},
            ],
            "clusters": [{"cluster_id": "H002", "recommended_levers": [3, 5]}],
        }],
    }
    violations = check_i2_lever_coherence(evidence)
    assert any(v["invariant_id"] == "I2" and "ag_levers_missing_recommended" in v["title"]
               for v in violations), violations


def test_i2_green_when_levers_coherent() -> None:
    from genie_space_optimizer.optimization.invariants import check_i2_lever_coherence

    evidence = {
        "iterations": [{
            "iteration": 1,
            "ags": [{
                "id": "AG1",
                "levers": [3, 5, 6],
                "source_cluster_ids": ["H002"],
            }],
            "applied_patches": [
                {"ag_id": "AG1", "lever": 5, "proposal_id": "P1"},
                {"ag_id": "AG1", "lever": 6, "proposal_id": "P2"},
            ],
            "clusters": [{"cluster_id": "H002", "recommended_levers": [3, 5]}],
        }],
    }
    assert check_i2_lever_coherence(evidence) == []


def test_i3_red_when_buckets_do_not_partition_target_qids() -> None:
    from genie_space_optimizer.optimization.invariants import check_i3_acceptance_buckets

    evidence = {"iterations": [{
        "iteration": 1,
        "acceptance_decision": {
            "target_qids": ["q_026"],
            "target_fixed_qids": [],
            "target_still_hard_qids": [],
            "reason_code": "target_qids_not_improved",
        },
    }]}
    violations = check_i3_acceptance_buckets(evidence)
    assert any(v["invariant_id"] == "I3" for v in violations), violations


def test_i3_green_when_buckets_partition_and_reason_names_bucket() -> None:
    from genie_space_optimizer.optimization.invariants import check_i3_acceptance_buckets

    evidence = {"iterations": [{
        "iteration": 1,
        "acceptance_decision": {
            "target_qids": ["q_026"],
            "target_fixed_qids": [],
            "target_still_hard_qids": ["q_026"],
            "reason_code": "target_still_hard_qids",
        },
    }]}
    assert check_i3_acceptance_buckets(evidence) == []


def test_i3_red_when_qid_in_two_buckets() -> None:
    from genie_space_optimizer.optimization.invariants import check_i3_acceptance_buckets

    evidence = {"iterations": [{
        "iteration": 1,
        "acceptance_decision": {
            "target_qids": ["q_026"],
            "target_fixed_qids": ["q_026"],
            "target_still_hard_qids": ["q_026"],
            "reason_code": "target_fixed_qids",
        },
    }]}
    assert any(
        v["invariant_id"] == "I3" and "double_counted" in v["title"]
        for v in check_i3_acceptance_buckets(evidence)
    )


def test_i4_red_on_consecutive_empty_proposals_same_ag() -> None:
    from genie_space_optimizer.optimization.invariants import check_i4_no_silent_retry

    evidence = {"iterations": [
        {"iteration": 1, "selected_ag_id": "AG1", "proposal_count": 0},
        {"iteration": 2, "selected_ag_id": "AG1", "proposal_count": 0},
    ]}
    violations = check_i4_no_silent_retry(evidence)
    assert any(v["invariant_id"] == "I4" for v in violations)


def test_i4_red_on_same_body_fingerprint_set_after_rollback() -> None:
    from genie_space_optimizer.optimization.invariants import check_i4_no_silent_retry

    evidence = {"iterations": [
        {
            "iteration": 1, "selected_ag_id": "AG_H004",
            "proposal_count": 4,
            "applied_patch_body_fingerprints": ["fp_a", "fp_b"],
            "acceptance_decision": {"reason_code": "target_still_hard_qids"},
        },
        {
            "iteration": 2, "selected_ag_id": "AG_H004",
            "proposal_count": 4,
            "applied_patch_body_fingerprints": ["fp_a", "fp_b"],
            "acceptance_decision": {},
        },
    ]}
    violations = check_i4_no_silent_retry(evidence)
    assert any(
        v["invariant_id"] == "I4" and "same_body_fingerprints" in v["title"]
        for v in violations
    )


def test_i4_green_when_ag_rotates() -> None:
    from genie_space_optimizer.optimization.invariants import check_i4_no_silent_retry

    evidence = {"iterations": [
        {"iteration": 1, "selected_ag_id": "AG_H004", "proposal_count": 0},
        {"iteration": 2, "selected_ag_id": "AG_H001", "proposal_count": 3},
    ]}
    assert check_i4_no_silent_retry(evidence) == []


def test_i5_red_on_illegal_trunk_transitions() -> None:
    from genie_space_optimizer.optimization.invariants import check_i5_replay_validity

    evidence = {
        "replay_validation": {
            "is_valid": False,
            "violation_count": 4,
            "violation_details": {"trunk: clustered -> already_passing": 4},
        },
    }
    violations = check_i5_replay_validity(evidence)
    assert any(v["invariant_id"] == "I5" for v in violations)
    assert violations[0]["violation_count"] == 4


def test_i5_green_when_replay_is_valid() -> None:
    from genie_space_optimizer.optimization.invariants import check_i5_replay_validity

    evidence = {
        "replay_validation": {
            "is_valid": True, "violation_count": 0, "violation_details": {},
        },
    }
    assert check_i5_replay_validity(evidence) == []


def test_i6_red_when_declared_paths_not_materialized() -> None:
    from genie_space_optimizer.optimization.invariants import check_i6_manifest_paths

    evidence = {"manifest": {
        "declared_paths": ["a", "b", "c"],
        "materialized_paths": ["a"],
    }}
    violations = check_i6_manifest_paths(evidence)
    assert any(v["invariant_id"] == "I6" for v in violations)
    v = violations[0]
    assert sorted(v["missing_paths"]) == ["b", "c"]


def test_i6_green_when_paths_equal() -> None:
    from genie_space_optimizer.optimization.invariants import check_i6_manifest_paths

    evidence = {"manifest": {
        "declared_paths": ["a", "b"],
        "materialized_paths": ["a", "b"],
    }}
    assert check_i6_manifest_paths(evidence) == []


def test_i7_red_when_open_cluster_has_no_rca_card_or_block_record() -> None:
    from genie_space_optimizer.optimization.invariants import check_i7_rca_grounding

    evidence = {"iterations": [{
        "iteration": 1,
        "open_hard_cluster_ids": ["H001", "H003", "H004", "H005"],
        "rca_cards_present": {"H001": False, "H003": False, "H004": False, "H005": False},
        "decision_records": [],
    }]}
    violations = check_i7_rca_grounding(evidence)
    ungrounded = {v.get("cluster_id") for v in violations if v["invariant_id"] == "I7"}
    assert ungrounded == {"H001", "H003", "H004", "H005"}


def test_i7_green_when_block_record_emitted() -> None:
    from genie_space_optimizer.optimization.invariants import check_i7_rca_grounding

    evidence = {"iterations": [{
        "iteration": 1,
        "open_hard_cluster_ids": ["H001"],
        "rca_cards_present": {"H001": False},
        "decision_records": [
            {
                "decision_type": "cluster_blocked_no_rca",
                "cluster_id": "H001",
            }
        ],
    }]}
    assert check_i7_rca_grounding(evidence) == []


def test_i7_green_when_rca_card_present() -> None:
    from genie_space_optimizer.optimization.invariants import check_i7_rca_grounding

    evidence = {"iterations": [{
        "iteration": 1,
        "open_hard_cluster_ids": ["H002"],
        "rca_cards_present": {"H002": True},
        "decision_records": [],
    }]}
    assert check_i7_rca_grounding(evidence) == []
