"""Cycle 11 — Phase H declared-vs-materialized path validator.

Pure helper: takes (declared_paths, materialized_paths) and returns
a list of ``manifest_path_missing`` dicts for the difference. The
harness wires it after _build_manifest using the live MLflow listing.
"""

from __future__ import annotations


def test_validator_reports_missing_paths() -> None:
    from genie_space_optimizer.optimization.run_output_contract import (
        validate_phase_h_manifest_paths,
    )

    declared = [
        "gso_postmortem_bundle/decision_trace_all.json",
        "gso_postmortem_bundle/iterations/iter_01/summary.json",
        "gso_postmortem_bundle/manifest.json",
    ]
    materialized = [
        "gso_postmortem_bundle/manifest.json",
    ]

    missing = validate_phase_h_manifest_paths(
        declared_paths=declared, materialized_paths=materialized,
    )
    paths = sorted(m["artifact_path"] for m in missing)
    assert paths == [
        "gso_postmortem_bundle/decision_trace_all.json",
        "gso_postmortem_bundle/iterations/iter_01/summary.json",
    ]
    assert all(m["kind"] == "manifest_path_missing" for m in missing)


def test_validator_returns_empty_when_all_present() -> None:
    from genie_space_optimizer.optimization.run_output_contract import (
        validate_phase_h_manifest_paths,
    )

    declared = ["a", "b"]
    materialized = ["a", "b", "c"]
    assert validate_phase_h_manifest_paths(
        declared_paths=declared, materialized_paths=materialized,
    ) == []


def test_phase_h_manifest_strict_validation_flag_default_on(monkeypatch) -> None:
    monkeypatch.delenv("GSO_PHASE_H_MANIFEST_STRICT_VALIDATION", raising=False)
    from genie_space_optimizer.common.config import (
        phase_h_manifest_strict_validation_enabled,
    )
    assert phase_h_manifest_strict_validation_enabled() is True
