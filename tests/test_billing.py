from order_desk.api.billing import (
    PLAN_PRICES_CENTS,
    MockBillingClient,
    build_billing,
    lookup_key,
)
from order_desk.api.tenancy import Plan


def test_plan_prices_defined() -> None:
    assert PLAN_PRICES_CENTS[Plan.FREE] == 0
    assert PLAN_PRICES_CENTS[Plan.PRO] > 0
    assert PLAN_PRICES_CENTS[Plan.ENTERPRISE] > PLAN_PRICES_CENTS[Plan.PRO]


def test_lookup_key_stable() -> None:
    assert lookup_key(Plan.PRO) == "order_desk_pro"


def test_build_billing_without_key_is_mock() -> None:
    client = build_billing(None)
    assert isinstance(client, MockBillingClient)


def test_mock_ensure_prices_all_plans() -> None:
    prices = MockBillingClient().ensure_prices()
    assert set(prices.keys()) == set(Plan)


def test_mock_customer_and_subscription_flow() -> None:
    client = MockBillingClient()
    cid = client.create_customer("o1", "Acme", "billing@acme.test")
    assert cid.startswith("cus_")
    sub = client.subscribe(cid, Plan.PRO)
    assert sub.customer_id == cid
    assert sub.plan == Plan.PRO
    assert sub.status == "active"
    # retrievable
    got = client.get_subscription(sub.subscription_id)
    assert got.subscription_id == sub.subscription_id


def test_mock_subscriptions_have_distinct_ids() -> None:
    client = MockBillingClient()
    cid = client.create_customer("o1", "Acme", "b@acme.test")
    s1 = client.subscribe(cid, Plan.PRO)
    s2 = client.subscribe(cid, Plan.ENTERPRISE)
    assert s1.subscription_id != s2.subscription_id
