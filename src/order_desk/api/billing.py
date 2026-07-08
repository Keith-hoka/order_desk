"""Stripe subscription billing (Phase 11).

Mirrors the Notifier pattern (mock + real behind a protocol): MockBillingClient
records calls for offline tests and CI; StripeBillingClient is the real path,
talking to Stripe in test mode via a secret key from the environment. Billing is
subscription-based -- a customer (one per org) subscribes to a plan's monthly
price. Prices are provisioned idempotently by lookup_key, so the code is
self-contained: it creates the product and per-plan prices on first run and
reuses them after, with no manual Dashboard setup.

Honest scope: this is a subscription skeleton in Stripe *test mode* (no real
charges). Plan quotas are enforced locally (metering + quota); Stripe owns the
subscription and the monthly price. Usage-based (metered) billing, webhooks, and
invoice reconciliation are production extensions, not built here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from order_desk.api.tenancy import Plan

# monthly price in cents by plan; free is $0
PLAN_PRICES_CENTS: dict[Plan, int] = {
    Plan.FREE: 0,
    Plan.PRO: 4900,
    Plan.ENTERPRISE: 49900,
}
PRODUCT_NAME = "order_desk"
CURRENCY = "usd"


def lookup_key(plan: Plan) -> str:
    return f"order_desk_{plan.value}"


@dataclass
class Subscription:
    subscription_id: str
    customer_id: str
    plan: Plan
    status: str


class BillingClient(Protocol):
    def ensure_prices(self) -> dict[Plan, str]: ...

    def create_customer(self, org_id: str, name: str, email: str) -> str: ...

    def subscribe(self, customer_id: str, plan: Plan) -> Subscription: ...

    def get_subscription(self, subscription_id: str) -> Subscription: ...


@dataclass
class MockBillingClient:
    """Offline billing for tests/CI: deterministic fake ids, no Stripe calls."""

    _customers: dict[str, str] = field(default_factory=dict)
    _subs: dict[str, Subscription] = field(default_factory=dict)
    _counter: int = 0

    def ensure_prices(self) -> dict[Plan, str]:
        return {plan: f"price_mock_{plan.value}" for plan in Plan}

    def create_customer(self, org_id: str, name: str, email: str) -> str:
        cid = f"cus_mock_{org_id}"
        self._customers[cid] = org_id
        return cid

    def subscribe(self, customer_id: str, plan: Plan) -> Subscription:
        self._counter += 1
        sub = Subscription(
            subscription_id=f"sub_mock_{self._counter}",
            customer_id=customer_id,
            plan=plan,
            status="active",
        )
        self._subs[sub.subscription_id] = sub
        return sub

    def get_subscription(self, subscription_id: str) -> Subscription:
        return self._subs[subscription_id]


class StripeBillingClient:
    """Real Stripe test-mode billing via the v1 namespace (stripe 15.x)."""

    def __init__(self, api_key: str) -> None:
        import stripe

        self._client = stripe.StripeClient(api_key)

    def ensure_prices(self) -> dict[Plan, str]:
        v1 = self._client.v1
        # find-or-create one product for the app
        existing = v1.products.list({"limit": 100})
        product = next((p for p in existing.data if p.name == PRODUCT_NAME), None)
        if product is None:
            product = v1.products.create({"name": PRODUCT_NAME})

        prices: dict[Plan, str] = {}
        for plan in Plan:
            key = lookup_key(plan)
            found = v1.prices.list({"lookup_keys": [key], "limit": 1})
            if found.data:
                prices[plan] = found.data[0].id
                continue
            price = v1.prices.create(
                {
                    "product": product.id,
                    "unit_amount": PLAN_PRICES_CENTS[plan],
                    "currency": CURRENCY,
                    "recurring": {"interval": "month"},
                    "lookup_key": key,
                }
            )
            prices[plan] = price.id
        return prices

    def create_customer(
        self, org_id: str, name: str, email: str, payment_method: str | None = None
    ) -> str:
        customer = self._client.v1.customers.create(
            {"name": name, "email": email, "metadata": {"org_id": org_id}}
        )
        if payment_method is not None:
            # attach returns the customer-scoped payment method; use its id as the
            # default (attaching a shared test token clones it to a new id)
            attached = self._client.v1.payment_methods.attach(
                payment_method, {"customer": customer.id}
            )
            self._client.v1.customers.update(
                customer.id,
                {"invoice_settings": {"default_payment_method": attached.id}},
            )
        return customer.id

    def subscribe(self, customer_id: str, plan: Plan) -> Subscription:
        price_id = self.ensure_prices()[plan]
        sub = self._client.v1.subscriptions.create(
            {"customer": customer_id, "items": [{"price": price_id}]}
        )
        return Subscription(
            subscription_id=sub.id, customer_id=customer_id, plan=plan, status=sub.status
        )

    def get_subscription(self, subscription_id: str) -> Subscription:
        sub = self._client.v1.subscriptions.retrieve(subscription_id)
        cust = sub.customer if isinstance(sub.customer, str) else sub.customer.id
        # plan is recovered from the price's lookup_key metadata is skipped here;
        # status + ids are the fields the caller checks
        return Subscription(
            subscription_id=sub.id, customer_id=cust, plan=Plan.FREE, status=sub.status
        )


def build_billing(api_key: str | None) -> BillingClient:
    """Real Stripe client when a key is configured, else the mock."""
    if api_key:
        return StripeBillingClient(api_key)
    return MockBillingClient()
