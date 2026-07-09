"""Multi-tenant org/user model and plan tiers (Phase 11).

An Org is a billing tenant; a User belongs to one Org. Requests are scoped to
an org, and resources (usage, review items) are isolated by org_id at the
application layer -- a deliberate, honest choice for this skeleton: it proves
the multi-tenant shape without database row-level security, which a production
deployment would add. Plan tiers carry the monthly extraction quota that the
metering layer enforces.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Plan(StrEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# monthly extraction quota by plan; enterprise is effectively unlimited
# the org that owns the pre-tenancy Phase 7 review queue; unauthenticated or
# legacy items are attributed here so existing demo data stays visible
DEMO_ORG_ID = "org-demo"


PLAN_QUOTAS: dict[Plan, int] = {
    Plan.FREE: 100,
    Plan.PRO: 10_000,
    Plan.ENTERPRISE: 1_000_000,
}


@dataclass(frozen=True)
class Org:
    org_id: str
    name: str
    plan: Plan = Plan.FREE

    @property
    def monthly_quota(self) -> int:
        return PLAN_QUOTAS[self.plan]


@dataclass(frozen=True)
class User:
    user_id: str
    org_id: str
    role: str = "member"  # member | admin


# standard scopes granted by role
ROLE_SCOPES: dict[str, list[str]] = {
    "member": ["extract:write", "review:read", "review:write"],
    "admin": ["extract:write", "review:read", "review:write", "org:admin"],
}


def scopes_for_role(role: str) -> list[str]:
    return ROLE_SCOPES.get(role, ROLE_SCOPES["member"])
