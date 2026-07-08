from datetime import UTC, datetime

import pytest

from order_desk.api.metering import (
    InMemoryMeteringStore,
    SqliteMeteringStore,
    Usage,
    current_period,
)


def test_current_period_format() -> None:
    dt = datetime(2026, 7, 8, tzinfo=UTC)
    assert current_period(dt) == "2026-07"


# run the same behavioural suite against both stores
@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path):
    if request.param == "memory":
        return InMemoryMeteringStore()
    return SqliteMeteringStore(tmp_path / "metering.db")


def test_record_accumulates(store) -> None:
    store.record("o1", input_tokens=100, output_tokens=20, period="2026-07")
    store.record("o1", input_tokens=50, output_tokens=10, period="2026-07")
    u = store.usage("o1", period="2026-07")
    assert u.extractions == 2
    assert u.input_tokens == 150
    assert u.output_tokens == 30
    assert u.total_tokens == 180


def test_usage_isolated_by_org(store) -> None:
    store.record("o1", input_tokens=100, output_tokens=20, period="2026-07")
    store.record("o2", input_tokens=5, output_tokens=1, period="2026-07")
    assert store.usage("o1", "2026-07").extractions == 1
    assert store.usage("o2", "2026-07").input_tokens == 5
    assert store.usage("o3", "2026-07").extractions == 0  # unknown org -> zero


def test_usage_isolated_by_period(store) -> None:
    store.record("o1", input_tokens=100, output_tokens=20, period="2026-07")
    store.record("o1", input_tokens=100, output_tokens=20, period="2026-08")
    assert store.usage("o1", "2026-07").extractions == 1
    assert store.usage("o1", "2026-08").extractions == 1


def test_unknown_org_returns_empty_usage(store) -> None:
    u = store.usage("nobody", "2026-07")
    assert isinstance(u, Usage)
    assert u.extractions == 0
    assert u.total_tokens == 0


def test_sqlite_survives_reconnect(tmp_path) -> None:
    # durability: record, drop the store, reopen a fresh one on the same file
    db = tmp_path / "metering.db"
    store1 = SqliteMeteringStore(db)
    store1.record("o1", input_tokens=100, output_tokens=20, period="2026-07")
    del store1
    store2 = SqliteMeteringStore(db)  # fresh connection, same file
    u = store2.usage("o1", "2026-07")
    assert u.extractions == 1
    assert u.input_tokens == 100  # usage persisted across "restart"
