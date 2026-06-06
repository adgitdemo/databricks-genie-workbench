"""Watch settings router: conversation cache refresh and health."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.services import lakebase
from backend.services.auth import get_databricks_host
from backend.watch.models import HealthStatus
from backend.watch.services import (
    conversations_client,
    genie_client,
    system_tables,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/watch/settings")


@router.get("/health")
async def health() -> dict:
    try:
        host = get_databricks_host()
    except Exception:
        host = None
    return HealthStatus(
        lakebase_available=lakebase.is_available(),
        obo_active=False,
        warehouse_id=os.environ.get("SQL_WAREHOUSE_ID"),
        workspace_host=host,
        system_tables_accessible=system_tables.system_tables_status(),
    ).model_dump(mode="json")


@router.post("/cache/refresh")
async def refresh_cache(background_tasks: BackgroundTasks) -> dict:
    try:
        spaces = genie_client.list_genie_spaces()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"could not list spaces: {e}")
    for s in spaces:
        sid = s.get("id")
        if not sid:
            continue
        background_tasks.add_task(_safe_sync, sid)
    return {"queued": len(spaces)}


async def _safe_sync(space_id: str) -> None:
    try:
        await conversations_client.sync_space(space_id, fetch_messages=True)
    except Exception as e:
        logger.warning("sync_space(%s) failed: %s", space_id, e)
