"""Cycle 10 W5.2 — DOA fingerprint buffer matches across patch shapes."""
from __future__ import annotations


def test_buffer_contains_returns_true_for_body_match(monkeypatch):
    monkeypatch.setenv("GSO_DOA_FINGERPRINT_PATCH_BODY_MATCH", "1")
    from genie_space_optimizer.optimization.reflection_retry import (
        DoaFingerprintBuffer,
    )
    buf = DoaFingerprintBuffer()
    captured = {
        "patch_type": "update_instruction_section",
        "target_table": "tkt_doc",
        "target_column": "outbound_route_total_segments",
        "body": "Filter rows where outbound_route_total_segments = 1.",
    }
    candidate = {
        "patch_type": "rewrite_instruction",
        "target_table": "tkt_doc",
        "target_column": "outbound_route_total_segments",
        "content": (
            "Filter rows where outbound_route_total_segments = 1."
        ),
    }
    buf.add(ag_id="AG_X", patch=captured)
    assert buf.contains(ag_id="AG_X", patch=candidate) is True


def test_buffer_contains_flag_off_only_signature_matches(monkeypatch):
    monkeypatch.setenv("GSO_DOA_FINGERPRINT_PATCH_BODY_MATCH", "0")
    from genie_space_optimizer.optimization.reflection_retry import (
        DoaFingerprintBuffer,
    )
    buf = DoaFingerprintBuffer()
    captured = {
        "patch_type": "update_instruction_section",
        "target_table": "tkt_doc",
        "target_column": "outbound_route_total_segments",
        "body": "Filter rows where outbound_route_total_segments = 1.",
    }
    candidate = {
        "patch_type": "rewrite_instruction",  # different shape
        "target_table": "tkt_doc",
        "target_column": "outbound_route_total_segments",
        "content": (
            "Filter rows where outbound_route_total_segments = 1."
        ),
    }
    buf.add(ag_id="AG_X", patch=captured)
    assert buf.contains(ag_id="AG_X", patch=candidate) is False


def test_buffer_signature_match_works_with_flag_on(monkeypatch):
    monkeypatch.setenv("GSO_DOA_FINGERPRINT_PATCH_BODY_MATCH", "1")
    from genie_space_optimizer.optimization.reflection_retry import (
        DoaFingerprintBuffer,
    )
    buf = DoaFingerprintBuffer()
    p = {
        "patch_type": "update_instruction_section",
        "target_table": "tkt_doc",
        "target_column": "outbound_route_total_segments",
        "body": "X",
    }
    buf.add(ag_id="AG_X", patch=p)
    assert buf.contains(ag_id="AG_X", patch=p) is True
