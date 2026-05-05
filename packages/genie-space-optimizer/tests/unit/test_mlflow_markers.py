"""Phase E.0 Task 3 — stdout markers for artifact persistence outcomes."""

import json


def test_phase_a_artifact_marker_success_payload() -> None:
    from genie_space_optimizer.common.mlflow_markers import phase_a_artifact_marker

    line = phase_a_artifact_marker(
        optimization_run_id="run_1",
        iteration=4,
        anchor_run_id="abc123",
        artifact_path="phase_a/journey_validation/iter_4.json",
        success=True,
        exception_class="",
    )
    assert line.startswith("GSO_PHASE_A_ARTIFACT_V1 ")
    payload = json.loads(line[len("GSO_PHASE_A_ARTIFACT_V1 "):])
    assert payload == {
        "optimization_run_id": "run_1",
        "iteration": 4,
        "anchor_run_id": "abc123",
        "artifact_path": "phase_a/journey_validation/iter_4.json",
        "success": True,
        "exception_class": "",
    }


def test_phase_a_artifact_marker_failure_payload() -> None:
    from genie_space_optimizer.common.mlflow_markers import phase_a_artifact_marker

    line = phase_a_artifact_marker(
        optimization_run_id="run_1",
        iteration=4,
        anchor_run_id="",
        artifact_path="phase_a/journey_validation/iter_4.json",
        success=False,
        exception_class="MlflowException",
    )
    payload = json.loads(line[len("GSO_PHASE_A_ARTIFACT_V1 "):])
    assert payload["success"] is False
    assert payload["exception_class"] == "MlflowException"
    assert payload["anchor_run_id"] == ""


def test_phase_b_artifact_marker_emits_decision_and_transcript_paths() -> None:
    from genie_space_optimizer.common.mlflow_markers import phase_b_artifact_marker

    line = phase_b_artifact_marker(
        optimization_run_id="run_1",
        iteration=4,
        anchor_run_id="abc123",
        decision_trace_path="phase_b/decision_trace/iter_4.json",
        operator_transcript_path="phase_b/operator_transcript/iter_4.txt",
        success=True,
        exception_class="",
    )
    assert line.startswith("GSO_PHASE_B_ARTIFACT_V1 ")
    payload = json.loads(line[len("GSO_PHASE_B_ARTIFACT_V1 "):])
    assert payload["decision_trace_path"] == "phase_b/decision_trace/iter_4.json"
    assert payload["operator_transcript_path"] == "phase_b/operator_transcript/iter_4.txt"
    assert payload["success"] is True


# Cycle 10 — markers
def test_lever6_force_llm_declined_marker_shape():
    from genie_space_optimizer.common.mlflow_markers import (
        lever6_force_llm_declined_marker,
    )
    s = lever6_force_llm_declined_marker(
        run_id="r1", iteration=2, ag_id="AG_X",
        cluster_id="H004", root_cause="missing_filter",
    )
    assert s.startswith("GSO_LEVER6_FORCE_LLM_DECLINED_V1 ")


def test_lever6_force_raised_marker_shape():
    from genie_space_optimizer.common.mlflow_markers import (
        lever6_force_raised_marker,
    )
    s = lever6_force_raised_marker(
        run_id="r1", iteration=2, ag_id="AG_X",
        cluster_id="H004", root_cause="missing_filter",
        exception_repr="ValueError('boom')",
    )
    assert s.startswith("GSO_LEVER6_FORCE_RAISED_V1 ")


def test_narrow_not_applicable_marker_shape():
    from genie_space_optimizer.common.mlflow_markers import (
        narrow_not_applicable_marker,
    )
    s = narrow_not_applicable_marker(
        run_id="r1", iteration=3, ag_id="AG_X",
        cluster_id="H001", root_cause="missing_filter",
        original_patch_type="add_sql_snippet_measure",
        reason="patch_type_lacks_where_predicate",
    )
    assert s.startswith("GSO_NARROW_NOT_APPLICABLE_V1 ")


def test_ag_levers_unioned_marker_shape():
    from genie_space_optimizer.common.mlflow_markers import (
        ag_levers_unioned_marker,
    )
    s = ag_levers_unioned_marker(
        run_id="r1", iteration=2, ag_id="AG_X", cluster_id="H001",
        levers_before=("5",), levers_after=("3", "5", "6"),
    )
    assert s.startswith("GSO_AG_LEVERS_UNIONED_V1 ")
