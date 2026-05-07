"""Preflight checks for the notebook installer."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import sys
from typing import Any
from urllib.parse import quote

from genie_space_optimizer.common.prompt_registry import check_prompt_registry
from genie_space_optimizer.common.prompt_registry import REASON_FEATURE_NOT_ENABLED

from .apps import APP_SCOPES, api_do, get_app
from .config import InstallConfig


@dataclass(frozen=True)
class PreflightIssue:
    check: str
    message: str
    remediation: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PreflightResult:
    checks: list[str]
    warnings: list[PreflightIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": self.checks,
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


class PreflightError(RuntimeError):
    def __init__(self, issues: list[PreflightIssue]):
        self.issues = issues
        lines = ["Notebook installer preflight failed:"]
        for issue in issues:
            lines.append(f"- {issue.check}: {issue.message} Remediation: {issue.remediation}")
        super().__init__("\n".join(lines))


def _probe_api(w, method: str, path: str, check: str, remediation: str) -> PreflightIssue | None:
    try:
        api_do(w, method, path)
        return None
    except Exception as exc:  # noqa: BLE001 - preserve Databricks SDK detail
        return PreflightIssue(
            check=check,
            message=str(exc),
            remediation=remediation,
        )


def _path_exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def run_preflight(w, cfg: InstallConfig, *, repo_root: Path | None = None) -> PreflightResult:
    """Validate prerequisites that commonly fail notebook installs.

    The checks are intentionally read-only except for the separate app-scope
    probe below, which requires an app to exist. This function should run
    before expensive provisioning.
    """
    cfg = cfg.normalized()
    issues: list[PreflightIssue] = []
    warnings: list[PreflightIssue] = []
    checks: list[str] = []

    checks.append("python-runtime")
    if sys.version_info < (3, 11):
        issues.append(
            PreflightIssue(
                check="python-runtime",
                message=(
                    f"Python {sys.version_info.major}.{sys.version_info.minor} is attached. "
                    "The notebook installer expects Python 3.11+."
                ),
                remediation="Attach the notebook to Databricks Serverless Environment v5 and rerun it.",
            )
        )

    root = repo_root or Path(cfg.repo_root or "")
    checks.append("repo-root")
    for rel in ("app.yaml", "pyproject.toml", "uv.lock", "package.json"):
        if not _path_exists(root / rel):
            issues.append(
                PreflightIssue(
                    check="repo-root",
                    message=f"Required repository file is missing: {rel}",
                    remediation="Run the notebook from the cloned Databricks Git folder for this repository.",
                )
            )

    checks.append("sql-warehouse")
    warehouse = quote(cfg.warehouse_id, safe="")
    issue = _probe_api(
        w,
        "GET",
        f"/api/2.0/sql/warehouses/{warehouse}",
        "sql-warehouse",
        "Verify warehouse_id is correct and that you have CAN_USE on the SQL warehouse.",
    )
    if issue:
        issues.append(issue)

    checks.append("catalog")
    catalog = quote(cfg.catalog, safe="")
    issue = _probe_api(
        w,
        "GET",
        f"/api/2.1/unity-catalog/catalogs/{catalog}",
        "catalog",
        "Verify the catalog exists and that you have USE CATALOG and CREATE SCHEMA privileges.",
    )
    if issue:
        issues.append(issue)

    checks.append("llm-model-serving-endpoint")
    endpoint = quote(cfg.llm_model, safe="")
    issue = _probe_api(
        w,
        "GET",
        f"/api/2.0/serving-endpoints/{endpoint}",
        "llm-model-serving-endpoint",
        "Verify llm_model is a serving endpoint name that exists in this workspace.",
    )
    if issue:
        issues.append(issue)

    if cfg.mlflow_experiment_id:
        checks.append("mlflow-experiment")
        experiment_id = quote(cfg.mlflow_experiment_id, safe="")
        issue = _probe_api(
            w,
            "GET",
            f"/api/2.0/mlflow/experiments/get?experiment_id={experiment_id}",
            "mlflow-experiment",
            "Use an MLflow experiment ID from this workspace, or leave mlflow_experiment_id blank.",
        )
        if issue:
            issues.append(issue)

    checks.append("mlflow-prompt-registry")
    probe = check_prompt_registry(w, mode="read", uc_schema=None, bypass_cache=True)
    if not probe.available:
        if getattr(probe, "reason_code", "") == REASON_FEATURE_NOT_ENABLED:
            remediation = (
                "Ask a workspace admin to enable the MLflow Prompt Registry beta "
                "from the Databricks Previews page."
            )
        else:
            remediation = (
                "Prompt Registry appears enabled but the availability probe failed. "
                "Retry the installer after pulling the latest notebook code; if it still fails, "
                "share the trace ID and error code with Databricks support."
            )
        issues.append(
            PreflightIssue(
                check="mlflow-prompt-registry",
                message=probe.user_message or probe.raw_error or "MLflow Prompt Registry probe failed.",
                remediation=remediation,
            )
        )

    if cfg.lakebase_mode == "skip":
        warnings.append(
            PreflightIssue(
                check="lakebase",
                message="Lakebase provisioning is disabled; app state will use in-memory storage.",
                remediation="Set lakebase_mode to create or existing if persistent scan history is required.",
            )
        )

    if issues:
        raise PreflightError(issues)
    return PreflightResult(checks=checks, warnings=warnings)


def verify_app_user_authorization_scopes(w, app_name: str) -> None:
    """Fail early when Apps user authorization scopes cannot be configured."""
    app = get_app(w, app_name) or {}
    resources = app.get("resources") or []
    try:
        api_do(
            w,
            "PATCH",
            f"/api/2.0/apps/{app_name}",
            {
                "user_api_scopes": APP_SCOPES,
                "resources": resources,
            },
        )
    except Exception as exc:  # noqa: BLE001 - preserve Databricks SDK detail
        raise RuntimeError(
            "Databricks Apps user authorization is required but scopes could not be configured. "
            "Ask a workspace admin to enable Databricks Apps On-Behalf-of-User authorization "
            "from the Databricks Previews page, then restart existing apps before rerunning "
            f"the installer. Underlying error: {exc}"
        ) from exc
