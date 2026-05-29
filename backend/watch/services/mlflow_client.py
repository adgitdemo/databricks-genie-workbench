"""MLflow tracking helpers for the GenieWatch evals tab."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _client():
    from mlflow.tracking import MlflowClient

    # The process-global tracking URI is set once at startup in backend/main.py.
    # MlflowClient(tracking_uri=...) sets it per-instance, so we don't re-set the
    # global on every request.
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "databricks")
    return MlflowClient(tracking_uri=tracking_uri)


def get_experiment(experiment_id: str) -> Optional[dict[str, Any]]:
    if not experiment_id:
        return None
    try:
        exp = _client().get_experiment(experiment_id)
    except Exception as e:
        logger.info("get_experiment(%s) failed: %s", experiment_id, e)
        return None
    if not exp:
        return None
    return {
        "experiment_id": exp.experiment_id,
        "name": exp.name,
        "lifecycle_stage": exp.lifecycle_stage,
        "artifact_location": exp.artifact_location,
        "creation_time": exp.creation_time,
        "last_update_time": exp.last_update_time,
        "tags": dict(exp.tags or {}),
    }


def search_runs(experiment_id: str, max_results: int = 50) -> list[dict[str, Any]]:
    if not experiment_id:
        return []
    try:
        runs = _client().search_runs(
            experiment_ids=[experiment_id],
            max_results=max_results,
            order_by=["start_time DESC"],
        )
    except Exception as e:
        logger.info("search_runs(%s) failed: %s", experiment_id, e)
        return []
    out = []
    for r in runs:
        info = r.info
        data = r.data
        out.append({
            "run_id": info.run_id,
            "run_name": info.run_name,
            "status": info.status,
            "start_time": info.start_time,
            "end_time": info.end_time,
            "user_id": info.user_id,
            "metrics": dict(data.metrics or {}),
            "params": dict(data.params or {}),
            "tags": {k: v for k, v in (data.tags or {}).items() if not k.startswith("mlflow.")},
        })
    return out


def find_experiment_by_space_tag(space_id: str) -> Optional[str]:
    """Return the experiment_id the GSO pipeline created for *space_id*, if any.

    The optimization preflight tags its experiment with ``genie.space_id`` (see
    packages/genie-space-optimizer .../optimization/preflight.py). We search for a
    matching experiment so the Evals tab can auto-discover it instead of requiring
    a manual Settings mapping. Returns the most-recently-updated match.
    """
    if not space_id:
        return None
    try:
        exps = _client().search_experiments(
            filter_string=f"tags.`genie.space_id` = '{space_id}'",
        )
    except Exception as e:
        logger.info("search_experiments(genie.space_id=%s) failed: %s", space_id, e)
        return None
    if not exps:
        return None
    best = max(exps, key=lambda x: x.last_update_time or x.creation_time or 0)
    return best.experiment_id


def get_run(run_id: str) -> Optional[dict[str, Any]]:
    if not run_id:
        return None
    try:
        r = _client().get_run(run_id)
    except Exception as e:
        logger.info("get_run(%s) failed: %s", run_id, e)
        return None
    return {
        "run_id": r.info.run_id,
        "run_name": r.info.run_name,
        "status": r.info.status,
        "start_time": r.info.start_time,
        "end_time": r.info.end_time,
        "experiment_id": r.info.experiment_id,
        "metrics": dict(r.data.metrics or {}),
        "params": dict(r.data.params or {}),
        "tags": dict(r.data.tags or {}),
    }
