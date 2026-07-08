"""Construct controlled blended over-extraction cases (Phase 9.2).

Blended over-extraction is a known adapter weakness (Phase 3): on an email that
both orders product X and merely asks about product Y, the fine-tune tends to
pull Y into the order. In real mail this pattern is rare (the human slice's
question-mark orders are mostly process questions or polite ordering, not
genuine product inquiries), so we construct a controlled slice to demonstrate
the flywheel targeting this weakness.

Each case orders one or two catalog products (with quantities) and, in a
separate sentence, inquires about a product from a *different* category. The
gold contains only the ordered products -- the inquired product must not be
extracted. To keep the adapter learning the semantics (intent to order) rather
than a surface rule (a question mark means skip), a fraction of cases are
counter-examples: the "inquiry" is actually a polite order ("could I also get
20 rolls of ...?") and that product *does* belong in the gold.

This is a deliberately synthetic, controlled failure mode, labelled as such.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from order_desk.catalog import Catalog, Product, load_catalog
from order_desk.customers import load_customers

# order-line phrasings; {qty}/{unit}/{name}
ORDER_TEMPLATES = [
    "Please send {qty} {unit} of {name}.",
    "We'd like to order {qty} {unit} of {name}.",
    "Can we get {qty} {unit} of {name} please.",
    "Could you supply {qty} {unit} of {name}.",
    "Please put us down for {qty} {unit} of {name}.",
]

# genuine inquiry (NOT an order) about a product; gold excludes it
INQUIRY_TEMPLATES = [
    "Do you also stock {name}?",
    "What's the price on {name} these days?",
    "Do you carry {name} at all?",
    "Just wondering if you have {name} available.",
    "Out of interest, do you sell {name}?",
    "Is {name} something you supply?",
]

# counter-examples: phrased as a question but genuinely ordering; gold INCLUDES it
COUNTER_TEMPLATES = [
    "Could I also get {qty} {unit} of {name}?",
    "And can you add {qty} {unit} of {name} to that?",
    "Would it be possible to include {qty} {unit} of {name} as well?",
]

UNITS = ["each", "rolls", "boxes", "cartons", "units"]


@dataclass
class BlendedCase:
    id: str
    subject: str
    body: str
    gold_extraction: dict
    is_counter_example: bool  # True if the "inquiry" product is actually ordered


def _line(product: Product, qty: int, unit: str) -> dict:
    return {
        "product_text": product.name,
        "quantity": qty,
        "unit_text": unit,
        "unit_price_text": None,
        "item_notes": None,
    }


def _gold(order_lines: list[dict], buyer: str, address: str, po: str | None) -> dict:
    return {
        "customer_po_text": po,
        "requested_date_text": None,
        "delivery_address_text": address,
        "buyer_name_text": buyer,
        "notes": None,
        "line_items": order_lines,
    }


def _pick_different_category(rng: random.Random, catalog: Catalog, avoid: set[str]) -> Product:
    """Pick a product whose category is not in `avoid`."""
    candidates = [p for p in catalog.products if p.category not in avoid and p.active]
    return rng.choice(candidates)


def generate_blended_cases(
    n: int, seed: int, counter_fraction: float = 0.22, id_prefix: str = "BLD"
) -> list[BlendedCase]:
    rng = random.Random(seed)
    catalog = load_catalog()
    book = load_customers()
    customers = book.customers
    active = [p for p in catalog.products if p.active]

    cases: list[BlendedCase] = []
    for i in range(n):
        cust = rng.choice(customers)
        contact = rng.choice(cust.contacts)
        buyer = contact.name.split()[0]
        addr = rng.choice(cust.delivery_addresses).label
        po = None
        if cust.po_template and rng.random() < 0.5:
            po = cust.po_template.replace("#####", f"{rng.randint(10000, 99999)}")

        # order product(s): 1-2 from the same category
        order_product = rng.choice(active)
        order_qty = rng.randint(max(order_product.moq, 5), min(order_product.max_qty, 500))
        order_unit = rng.choice(UNITS)
        order_lines = [_line(order_product, order_qty, order_unit)]

        order_sentence = rng.choice(ORDER_TEMPLATES).format(
            qty=order_qty, unit=order_unit, name=order_product.name
        )

        # second product: from a DIFFERENT category, either inquired or (counter) ordered
        second = _pick_different_category(rng, catalog, avoid={order_product.category})
        is_counter = rng.random() < counter_fraction

        if is_counter:
            sec_qty = rng.randint(max(second.moq, 5), min(second.max_qty, 500))
            sec_unit = rng.choice(UNITS)
            second_sentence = rng.choice(COUNTER_TEMPLATES).format(
                qty=sec_qty, unit=sec_unit, name=second.name
            )
            order_lines.append(_line(second, sec_qty, sec_unit))  # counter: goes in gold
        else:
            second_sentence = rng.choice(INQUIRY_TEMPLATES).format(name=second.name)
            # inquiry: NOT in gold

        # assemble body (order first or inquiry first, varied)
        parts = [order_sentence, second_sentence]
        if rng.random() < 0.4:
            parts.reverse()
        body = f"Hi,\n\n{' '.join(parts)}\n\nThanks,\n{buyer}"
        subject = rng.choice(["order", "supplies", "restock", f"order for {addr}"])

        gold = _gold(order_lines, buyer, addr, po)
        cases.append(
            BlendedCase(
                id=f"{id_prefix}-{i:04d}",
                subject=subject,
                body=body,
                gold_extraction=gold,
                is_counter_example=is_counter,
            )
        )
    return cases


def case_to_record(case: BlendedCase) -> dict:
    """Convert to the record shape used by scoring and SFT."""
    return {
        "id": case.id,
        "email_class": "new_order",
        "subject": case.subject,
        "body": case.body,
        "gold_extraction": case.gold_extraction,
    }
