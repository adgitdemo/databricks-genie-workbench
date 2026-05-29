"""Authorization guards for the GenieWatch surface.

GenieWatch introduces SP-privileged, cross-workspace operations (manual rollup
refresh, system-table reads) that don't fit the workbench model where every
authenticated user can do everything. As a minimal first step, the admin-only
write endpoints are gated to workspace admins. A broader operator-vs-manager
role model is tracked as a follow-up.
"""

from __future__ import annotations

import os

from fastapi import HTTPException, Request


def is_admin_request(request: Request) -> bool:
    """Whether the caller is a workspace admin.

    Mirrors the admin signal used by ``/api/auth/me``: ``X-Forwarded-Groups``
    (injected by Databricks Apps) contains ``admins``. Falls back to the local
    dev modes (``DEV_ADMIN=true``, or ``DEV_USER_EMAIL`` set with no OBO headers)
    so non-Apps deployments behave the same as ``/api/auth/me``.
    """
    groups = (request.headers.get("X-Forwarded-Groups") or "").lower()
    if "admins" in groups:
        return True
    if os.environ.get("DEV_ADMIN", "").lower() == "true":
        return True
    has_obo_user = bool(
        request.headers.get("X-Forwarded-User")
        or request.headers.get("X-Forwarded-Email")
    )
    if not has_obo_user and os.environ.get("DEV_USER_EMAIL"):
        return True
    return False


def require_admin(request: Request) -> None:
    """FastAPI dependency: 403 unless the caller is a workspace admin."""
    if not is_admin_request(request):
        raise HTTPException(
            status_code=403,
            detail="This operation requires workspace admin access.",
        )
