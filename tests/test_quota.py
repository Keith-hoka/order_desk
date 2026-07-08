import pytest

from order_desk.api.orgs import InMemoryOrgStore, SqliteOrgStore
from order_desk.api.tenancy import Org, Plan


@pytest.fixture(params=["memory", "sqlite"])
def org_store(request, tmp_path):
    if request.param == "memory":
        return InMemoryOrgStore()
    return SqliteOrgStore(tmp_path / "orgs.db")


def test_upsert_and_get(org_store) -> None:
    org_store.upsert(Org("o1", "Acme", Plan.PRO))
    got = org_store.get("o1")
    assert got is not None
    assert got.plan == Plan.PRO
    assert got.monthly_quota == 10_000


def test_get_unknown_returns_none(org_store) -> None:
    assert org_store.get("nobody") is None


def test_upsert_updates_plan(org_store) -> None:
    org_store.upsert(Org("o1", "Acme", Plan.FREE))
    org_store.upsert(Org("o1", "Acme", Plan.ENTERPRISE))  # upgrade
    assert org_store.get("o1").plan == Plan.ENTERPRISE


def test_sqlite_org_survives_reconnect(tmp_path) -> None:
    db = tmp_path / "orgs.db"
    s1 = SqliteOrgStore(db)
    s1.upsert(Org("o1", "Acme", Plan.PRO))
    del s1
    s2 = SqliteOrgStore(db)  # fresh connection, same file
    assert s2.get("o1").plan == Plan.PRO  # plan persisted
