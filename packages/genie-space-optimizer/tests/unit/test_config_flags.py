"""Cycle 10 — config-flag accessors for the seven workstreams."""
from __future__ import annotations


def test_rca_ungrounded_records_enabled_default_on(monkeypatch):
    monkeypatch.delenv("GSO_RCA_UNGROUNDED_RECORDS_ENABLED", raising=False)
    from genie_space_optimizer.common.config import (
        rca_ungrounded_records_enabled,
    )
    assert rca_ungrounded_records_enabled() is True


def test_rca_ungrounded_records_enabled_off(monkeypatch):
    monkeypatch.setenv("GSO_RCA_UNGROUNDED_RECORDS_ENABLED", "0")
    from genie_space_optimizer.common.config import (
        rca_ungrounded_records_enabled,
    )
    assert rca_ungrounded_records_enabled() is False


def test_ag_levers_union_recommended_default_on(monkeypatch):
    monkeypatch.delenv("GSO_AG_LEVERS_UNION_RECOMMENDED", raising=False)
    from genie_space_optimizer.common.config import (
        ag_levers_union_recommended_enabled,
    )
    assert ag_levers_union_recommended_enabled() is True


def test_ag_levers_union_recommended_off(monkeypatch):
    monkeypatch.setenv("GSO_AG_LEVERS_UNION_RECOMMENDED", "0")
    from genie_space_optimizer.common.config import (
        ag_levers_union_recommended_enabled,
    )
    assert ag_levers_union_recommended_enabled() is False


def test_lever6_force_typed_outcomes_default_on(monkeypatch):
    monkeypatch.delenv("GSO_LEVER6_FORCE_TYPED_OUTCOMES", raising=False)
    from genie_space_optimizer.common.config import (
        lever6_force_typed_outcomes_enabled,
    )
    assert lever6_force_typed_outcomes_enabled() is True


def test_lever6_force_typed_outcomes_off(monkeypatch):
    monkeypatch.setenv("GSO_LEVER6_FORCE_TYPED_OUTCOMES", "0")
    from genie_space_optimizer.common.config import (
        lever6_force_typed_outcomes_enabled,
    )
    assert lever6_force_typed_outcomes_enabled() is False
