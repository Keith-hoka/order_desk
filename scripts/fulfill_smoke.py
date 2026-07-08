"""End-to-end fulfillment smoke: resolve -> ERP -> real Slack (Phase 8.5).

Takes a couple of human orders, runs the real fulfillment path (resolve to
SKUs, build the ERP order, submit to the local sink, notify via the real Slack
webhook), and prints what happened. Demonstrates both outcomes: a clean order
submitted, and a held order needing manual mapping. Requires SLACK_WEBHOOK_URL.
The mock ERP writes to data/erp_orders_smoke.json.
"""

import os
import sys
from pathlib import Path

from order_desk.fulfillment.erp import LocalOrderSink
from order_desk.fulfillment.fulfill import fulfill_order
from order_desk.fulfillment.notify import build_notifier


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> None:
    load_dotenv()
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        sys.exit("SLACK_WEBHOOK_URL not set in .env")

    sink = LocalOrderSink("data/erp_orders_smoke.json")
    notifier = build_notifier(webhook)
    print(f"notifier: {type(notifier).__name__}")

    # a clean order (small carton, above moq) and a held one (unknown product)
    clean = {
        "customer_po_text": "PO-73218",
        "requested_date_text": None,
        "delivery_address_text": "Botany warehouse",
        "buyer_name_text": "Dana",
        "notes": None,
        "line_items": [
            {
                "product_text": "small carton",
                "quantity": 100,
                "unit_text": "each",
                "unit_price_text": None,
                "item_notes": None,
            },
            {
                "product_text": "medium carton",
                "quantity": 50,
                "unit_text": "each",
                "unit_price_text": None,
                "item_notes": None,
            },
        ],
    }
    held = {
        "customer_po_text": "PO-99001",
        "requested_date_text": None,
        "delivery_address_text": "Eagle Farm",
        "buyer_name_text": "Tom",
        "notes": None,
        "line_items": [
            {
                "product_text": "small carton",
                "quantity": 50,
                "unit_text": "each",
                "unit_price_text": None,
                "item_notes": None,
            },
            {
                "product_text": "artisanal unobtainium widget",
                "quantity": 5,
                "unit_text": None,
                "unit_price_text": None,
                "item_notes": None,
            },
        ],
    }

    print("\n=== clean order (PO-73218) ===")
    r1 = fulfill_order(clean, sink, notifier)
    print(f"  submitted: {r1.submitted}, order_id: {r1.order_id}, reason: {r1.reason}")

    print("\n=== held order (PO-99001, unknown product) ===")
    r2 = fulfill_order(held, sink, notifier)
    print(f"  submitted: {r2.submitted}, reason: {r2.reason}, unresolved: {r2.unresolved}")

    print("\nCheck your Slack channel for two messages: one ORDER_SUBMITTED, one NEEDS_MAPPING.")
    print("ERP orders written to data/erp_orders_smoke.json")


if __name__ == "__main__":
    main()
