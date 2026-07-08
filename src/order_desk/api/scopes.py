"""Scope-enforcing dependencies for org-scoped endpoints (Phase 11).

Builds on require_auth: when auth is enabled, an endpoint can require a specific
scope, and a principal lacking it is rejected with 403. When auth is disabled
(no secret -- dev/test), the principal is None and scope checks are skipped, so
local runs stay frictionless, matching the Phase 4 auth-disabled convention.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException

from order_desk.api.auth import Principal, require_auth


def require_scope(scope: str):
    """Return a dependency that enforces `scope` on the authenticated principal."""

    def dependency(principal: Principal | None = Depends(require_auth)) -> Principal | None:
        if principal is None:
            return None  # auth disabled -> no scope enforcement
        if not principal.has_scope(scope):
            raise HTTPException(status_code=403, detail=f"missing required scope: {scope}")
        return principal

    return dependency
