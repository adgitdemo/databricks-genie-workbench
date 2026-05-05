from __future__ import annotations

import pytest

from genie_space_optimizer.optimization.eval_concurrency import (
    EvalConcurrencyTier,
    adaptive_concurrency_enabled,
    concurrency_tier_for_attempt,
)


def test_attempt_1_uses_full_concurrency(monkeypatch):
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_SCORER_WORKERS_ATTEMPT_1", raising=False)
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_DATA_WORKERS_ATTEMPT_1", raising=False)
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_ADAPTIVE_CONCURRENCY", raising=False)
    tier = concurrency_tier_for_attempt(1)
    assert tier == EvalConcurrencyTier(data_workers=1, scorer_workers=8)


def test_attempt_2_degrades_scorer_workers(monkeypatch):
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_SCORER_WORKERS_ATTEMPT_2", raising=False)
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_ADAPTIVE_CONCURRENCY", raising=False)
    tier = concurrency_tier_for_attempt(2)
    assert tier.scorer_workers == 3
    assert tier.data_workers == 1


def test_attempt_3_collapses_to_one_worker(monkeypatch):
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_ADAPTIVE_CONCURRENCY", raising=False)
    tier = concurrency_tier_for_attempt(3)
    assert tier == EvalConcurrencyTier(data_workers=1, scorer_workers=1)


def test_attempt_beyond_3_pins_to_floor(monkeypatch):
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_ADAPTIVE_CONCURRENCY", raising=False)
    tier = concurrency_tier_for_attempt(99)
    assert tier == EvalConcurrencyTier(data_workers=1, scorer_workers=1)


def test_adaptive_concurrency_default_on(monkeypatch):
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_ADAPTIVE_CONCURRENCY", raising=False)
    assert adaptive_concurrency_enabled() is True


def test_adaptive_concurrency_can_be_disabled(monkeypatch):
    monkeypatch.setenv("GENIE_SPACE_OPTIMIZER_EVAL_ADAPTIVE_CONCURRENCY", "false")
    assert adaptive_concurrency_enabled() is False


def test_disabled_flag_returns_attempt_1_tier_for_all_attempts(monkeypatch):
    monkeypatch.setenv("GENIE_SPACE_OPTIMIZER_EVAL_ADAPTIVE_CONCURRENCY", "false")
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_SCORER_WORKERS_ATTEMPT_1", raising=False)
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_DATA_WORKERS_ATTEMPT_1", raising=False)
    tier_1 = concurrency_tier_for_attempt(1)
    tier_4 = concurrency_tier_for_attempt(4)
    assert tier_1 == tier_4
    assert tier_1 == EvalConcurrencyTier(data_workers=1, scorer_workers=8)


def test_env_overrides_apply(monkeypatch):
    monkeypatch.delenv("GENIE_SPACE_OPTIMIZER_EVAL_ADAPTIVE_CONCURRENCY", raising=False)
    monkeypatch.setenv("GENIE_SPACE_OPTIMIZER_EVAL_SCORER_WORKERS_ATTEMPT_1", "12")
    tier = concurrency_tier_for_attempt(1)
    assert tier.scorer_workers == 12
