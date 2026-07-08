"""Real Stripe test-mode smoke: provision prices, create a customer, subscribe.

Requires STRIPE_API_KEY (a test-mode sk_test_... key) in the environment. Talks
to Stripe in test mode -- no real charges. Verifies the subscription path end to
end: ensure the product+prices exist, create a customer for a demo org,
subscribe it to the Pro plan, and read the subscription back. Check the Stripe
test Dashboard afterwards for the customer and its active subscription.
"""

import os
from pathlib import Path

from order_desk.api.billing import StripeBillingClient, lookup_key
from order_desk.api.tenancy import Plan


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("STRIPE_API_KEY", "")
    if not api_key.startswith("sk_test_"):
        raise SystemExit("STRIPE_API_KEY must be a test-mode key (sk_test_...)")

    client = StripeBillingClient(api_key)

    print("ensuring product + prices ...")
    prices = client.ensure_prices()
    for plan in Plan:
        print(f"  {plan.value:<12} lookup={lookup_key(plan):<22} price_id={prices[plan]}")

    print("\ncreating customer for demo org 'org-smoke' (with test card) ...")
    # pm_card_visa is Stripe's built-in test payment method (test mode only)
    customer_id = client.create_customer(
        "org-smoke", "Smoke Test Co", "billing@smoke.test", payment_method="pm_card_visa"
    )
    print(f"  customer_id={customer_id}")

    print("\nsubscribing to Pro ...")
    sub = client.subscribe(customer_id, Plan.PRO)
    print(f"  subscription_id={sub.subscription_id} status={sub.status}")

    print("\nreading subscription back ...")
    got = client.get_subscription(sub.subscription_id)
    print(f"  status={got.status} customer={got.customer_id}")

    print("\nDone. Check the Stripe test Dashboard: Customers -> Smoke Test Co,")
    print("with an active Pro subscription. (Test mode -- no real charge.)")


if __name__ == "__main__":
    main()
