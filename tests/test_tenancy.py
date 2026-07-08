from order_desk.api.auth import decode_token, issue_token
from order_desk.api.tenancy import (
    PLAN_QUOTAS,
    Org,
    Plan,
    User,
    scopes_for_role,
)

SECRET = "test-secret"


def test_org_quota_by_plan() -> None:
    assert Org("o1", "Acme", Plan.FREE).monthly_quota == PLAN_QUOTAS[Plan.FREE]
    assert Org("o2", "BigCo", Plan.ENTERPRISE).monthly_quota == PLAN_QUOTAS[Plan.ENTERPRISE]
    assert Org("o3", "Default").plan == Plan.FREE  # default plan


def test_user_belongs_to_org() -> None:
    u = User("u1", "o1", role="admin")
    assert u.org_id == "o1"
    assert u.role == "admin"


def test_role_scopes() -> None:
    assert "org:admin" in scopes_for_role("admin")
    assert "org:admin" not in scopes_for_role("member")
    assert "extract:write" in scopes_for_role("member")
    # unknown role falls back to member scopes
    assert scopes_for_role("nonsense") == scopes_for_role("member")


def test_org_scoped_token_roundtrip() -> None:
    token = issue_token(SECRET, "u1", org_id="o1", scopes=scopes_for_role("admin"))
    principal = decode_token(SECRET, token)
    assert principal.sub == "u1"
    assert principal.org_id == "o1"
    assert principal.has_scope("org:admin")
    assert principal.has_scope("extract:write")


def test_token_without_org_is_backward_compatible() -> None:
    # old-style token: no org_id/scopes
    token = issue_token(SECRET, "legacy-client")
    principal = decode_token(SECRET, token)
    assert principal.sub == "legacy-client"
    assert principal.org_id is None
    assert principal.scopes == ()
    assert not principal.has_scope("extract:write")


def test_member_lacks_admin_scope() -> None:
    token = issue_token(SECRET, "u2", org_id="o1", scopes=scopes_for_role("member"))
    principal = decode_token(SECRET, token)
    assert principal.has_scope("review:write")
    assert not principal.has_scope("org:admin")
