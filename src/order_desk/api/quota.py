"""Per-org monthly quota enforcement (Phase 11).

Before an extraction runs, checks the org's usage this billing period against
its plan quota; if the org is at or over quota, the request is rejected with 429
and an upgrade hint. No-op when auth is disabled or the request carries no org
(backward-compatible with pre-tenancy tokens). Reads current usage from the
metering store and the plan from the org store -- the same stores that
accumulate usage and hold tenant plans.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from order_desk.api.auth import Principal, require_auth
from order_desk.api.metering import MeteringStore, current_period
from order_desk.api.orgs import OrgStore


def enforce_quota(
    request: Request,
    principal: Principal | None = Depends(require_auth),
) -> None:
    """Guard dependency: reject when the org is at or over its monthly quota."""
    if principal is None or principal.org_id is None:
        return  # auth disabled or no org -> no quota enforcement
    org_store: OrgStore | None = getattr(request.app.state, "org_store", None)
    metering: MeteringStore | None = getattr(request.app.state, "metering", None)
    if org_store is None or metering is None:
        return  # not configured -> no enforcement
    org = org_store.get(principal.org_id)
    if org is None:
        return  # unknown org -> do not block (org provisioning is separate)
    used = metering.usage(principal.org_id, current_period()).extractions
    if used >= org.monthly_quota:
        raise HTTPException(
            status_code=429,
            detail=(
                f"monthly quota reached ({used}/{org.monthly_quota} on the "
                f"{org.plan.value} plan); upgrade to continue"
            ),
        )
