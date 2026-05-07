from __future__ import annotations

import os
from types import SimpleNamespace

import pandas as pd
import pytest

from genie_space_optimizer.optimization import evaluation
from genie_space_optimizer.optimization.eval_watchdog import EvalHangTimeoutError


@pytest.fixture
def _clean_env(monkeypatch):
    for var in (
        "MLFLOW_GENAI_EVAL_MAX_WORKERS",
        "MLFLOW_GENAI_EVAL_MAX_SCORER_WORKERS",
        "MLFLOW_GENAI_EVAL_SKIP_TRACE_VALIDATION",
        "MLFLOW_GENAI_EVAL_ASYNC_TIMEOUT",
        "LITELLM_NUM_RETRIES",
        "GENIE_SPACE_OPTIMIZER_EVAL_DISABLE_LITELLM_RETRIES",
        "GENIE_SPACE_OPTIMIZER_EVAL_ADAPTIVE_CONCURRENCY",
        "GENIE_SPACE_OPTIMIZER_EVAL_WATCHDOG_ENABLED",
    ):
        monkeypatch.delenv(var, raising=False)
    # Module-level constants are computed at import time, so other tests
    # in the suite may have left them in a non-default state. Pin them to
    # the production-default values for the duration of the test.
    monkeypatch.setattr(evaluation, "EVAL_DISABLE_LITELLM_RETRIES", True)
    yield


def test_attempt_1_uses_tier_1_workers_and_disables_litellm_retries(monkeypatch, _clean_env):
    captured: list[dict[str, str]] = []

    def fake_evaluate(**_kwargs):
        captured.append(
            {
                "data_workers": os.environ.get("MLFLOW_GENAI_EVAL_MAX_WORKERS", ""),
                "scorer_workers": os.environ.get("MLFLOW_GENAI_EVAL_MAX_SCORER_WORKERS", ""),
                "litellm_retries": os.environ.get("LITELLM_NUM_RETRIES", ""),
                "skip_trace_validation": os.environ.get(
                    "MLFLOW_GENAI_EVAL_SKIP_TRACE_VALIDATION", ""
                ),
            }
        )
        return SimpleNamespace(metrics={}, tables={})

    monkeypatch.setattr(evaluation.mlflow.genai, "evaluate", fake_evaluate, raising=False)
    monkeypatch.setattr(evaluation, "_patch_mlflow_harness_none_trace", lambda: None)

    result, attempts = evaluation._run_evaluate_with_retries(
        evaluate_kwargs={"data": pd.DataFrame([{"q": 1}])}
    )

    assert result is not None
    assert captured[0]["data_workers"] == "1"
    assert captured[0]["scorer_workers"] == "8"
    assert captured[0]["litellm_retries"] == "0"
    assert captured[0]["skip_trace_validation"].lower() == "true"
    assert attempts[0]["status"] == "success"


def test_watchdog_timeout_is_classified_retryable_and_degrades(monkeypatch, _clean_env):
    call_count = {"n": 0}

    def fake_evaluate(**_kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise EvalHangTimeoutError("simulated hang")
        return SimpleNamespace(metrics={}, tables={})

    monkeypatch.setattr(evaluation.mlflow.genai, "evaluate", fake_evaluate, raising=False)
    monkeypatch.setattr(evaluation, "_patch_mlflow_harness_none_trace", lambda: None)
    monkeypatch.setattr(evaluation, "EVAL_RETRY_SLEEP_SECONDS", 0)

    result, attempts = evaluation._run_evaluate_with_retries(
        evaluate_kwargs={"data": pd.DataFrame([{"q": 1}])}
    )

    assert call_count["n"] == 2
    assert attempts[0]["status"] == "failed"
    assert attempts[0]["error_type"] == "EvalHangTimeoutError"
    assert attempts[1]["status"] == "success"
    # Attempt 2 must have used the degraded scorer worker count.
    assert attempts[1]["scorer_workers_attempt_2"] == "3"


def test_env_is_restored_after_run(monkeypatch, _clean_env):
    monkeypatch.setenv("MLFLOW_GENAI_EVAL_MAX_WORKERS", "preexisting-workers")
    monkeypatch.setenv("LITELLM_NUM_RETRIES", "preexisting-retries")

    def fake_evaluate(**_kwargs):
        return SimpleNamespace(metrics={}, tables={})

    monkeypatch.setattr(evaluation.mlflow.genai, "evaluate", fake_evaluate, raising=False)
    monkeypatch.setattr(evaluation, "_patch_mlflow_harness_none_trace", lambda: None)

    evaluation._run_evaluate_with_retries(
        evaluate_kwargs={"data": pd.DataFrame([{"q": 1}])}
    )

    assert os.environ["MLFLOW_GENAI_EVAL_MAX_WORKERS"] == "preexisting-workers"
    assert os.environ["LITELLM_NUM_RETRIES"] == "preexisting-retries"
