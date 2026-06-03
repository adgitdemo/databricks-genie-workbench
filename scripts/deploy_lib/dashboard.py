"""Create + publish the GenieWatch cost overview dashboard for notebook installs.

`deploy.sh` provisions this dashboard through the asset bundle and then reads its
id back into `app.yaml` as `DASHBOARD_COST_ID`. The notebook installer has no
bundle, so historically it shipped with the embed disabled. This module closes
that gap: it creates the same `dashboards/genie_spaces_overview.lvdash.json`
dashboard directly via the Lakeview API, publishes it with embedded credentials
(required for the app's embed-token mint), and grants the app service principal
CAN_RUN — returning the id so the caller can wire it into `app.yaml`.

Everything here is best-effort: a failure logs a warning and returns ``None`` so
the install still succeeds with the Cost embed hidden (the prior behavior).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from databricks.sdk.service.dashboards import Dashboard, DashboardView

from .config import InstallConfig
from .workspace_source import mkdirs

# Matches the bundle resource (databricks.yml -> dashboards.genie_spaces_overview).
DASHBOARD_DISPLAY_NAME = "Genie Workbench — Spaces Overview"
DASHBOARD_RELATIVE_PATH = "dashboards/genie_spaces_overview.lvdash.json"


@dataclass(frozen=True)
class DashboardInfo:
    dashboard_id: str
    display_name: str
    parent_path: str
    published: bool
    sp_grant_applied: bool


def dashboards_parent_path(deployer_user: str, app_name: str) -> str:
    return f"/Workspace/Users/{deployer_user}/{app_name}-resources/dashboards"


def _find_existing(w, parent_path: str, display_name: str) -> str | None:
    """Return the id of a live dashboard at parent_path/display_name, if any.

    Keeps re-runs idempotent — we update the existing dashboard in place rather
    than spawning a duplicate every install.
    """
    for d in w.lakeview.list(view=DashboardView.DASHBOARD_VIEW_BASIC):
        if d.display_name != display_name:
            continue
        if (d.parent_path or "") != parent_path:
            continue
        if d.lifecycle_state is not None and str(d.lifecycle_state).endswith("TRASHED"):
            continue
        if d.dashboard_id:
            return d.dashboard_id
    return None


def _grant_sp_can_run(w, dashboard_id: str, app_sp_client_id: str) -> bool:
    """Grant the app SP CAN_RUN — required so it can mint scoped embed tokens.

    Mirrors deploy.sh's PATCH /api/2.0/permissions/dashboards/{id}.
    """
    try:
        w.api_client.do(
            "PATCH",
            f"/api/2.0/permissions/dashboards/{dashboard_id}",
            body={
                "access_control_list": [
                    {
                        "service_principal_name": app_sp_client_id,
                        "permission_level": "CAN_RUN",
                    }
                ]
            },
        )
        return True
    except Exception:
        return False


def ensure_cost_dashboard(
    w,
    cfg: InstallConfig,
    app_sp_client_id: str,
    deployer_user: str,
) -> DashboardInfo:
    """Create/update + publish the cost dashboard and grant the app SP CAN_RUN.

    Returns ``DashboardInfo`` (including whether the SP grant applied). Raises on
    failure; the caller treats the dashboard as optional and falls back to an
    empty ``DASHBOARD_COST_ID`` (hiding the embed, matching deploy.sh).
    """
    source = Path(cfg.repo_root or "") / DASHBOARD_RELATIVE_PATH
    serialized = source.read_text(encoding="utf-8")

    parent_path = dashboards_parent_path(deployer_user, cfg.app_name)
    mkdirs(w, parent_path)

    # Reuse an existing dashboard at this path on re-runs rather than duplicating.
    existing_id = _find_existing(w, parent_path, DASHBOARD_DISPLAY_NAME)
    if existing_id:
        w.lakeview.update(
            existing_id,
            Dashboard(
                display_name=DASHBOARD_DISPLAY_NAME,
                serialized_dashboard=serialized,
                warehouse_id=cfg.warehouse_id,
            ),
        )
        dashboard_id = existing_id
    else:
        created = w.lakeview.create(
            Dashboard(
                display_name=DASHBOARD_DISPLAY_NAME,
                serialized_dashboard=serialized,
                warehouse_id=cfg.warehouse_id,
                parent_path=parent_path,
            )
        )
        dashboard_id = created.dashboard_id
        if not dashboard_id:
            raise RuntimeError("Lakeview create returned no dashboard_id")

    # Publishing with embedded SP credentials is what lets the app render the
    # dashboard via a scoped embed token (no viewer workspace session needed).
    w.lakeview.publish(
        dashboard_id,
        embed_credentials=True,
        warehouse_id=cfg.warehouse_id,
    )

    sp_grant_applied = _grant_sp_can_run(w, dashboard_id, app_sp_client_id)

    return DashboardInfo(
        dashboard_id=dashboard_id,
        display_name=DASHBOARD_DISPLAY_NAME,
        parent_path=parent_path,
        published=True,
        sp_grant_applied=sp_grant_applied,
    )
