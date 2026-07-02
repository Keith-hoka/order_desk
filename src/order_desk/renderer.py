"""Email renderer: weaves prose around scenario surfaces without touching them.

Contracts (locked in step 1.5):
- Extractor input is subject + body. po_surface may live in subject, body, or
  both (the po_placement dimension); every other label-bearing surface lives
  in the body exactly as the scenario fixed it.
- Prose may not introduce digits (digit-closure) or catalog terms
  (term-closure): masking every expected surface out of subject+body must
  leave no digit and no catalog name/alias/unit word. Price glue therefore
  never uses unit words ("@ $7.80", never "at $7.80 each").
- render_email is a pure function of (scenario, seed): a derived
  Random(f"{seed}|{scenario_id}") makes every email reproducible in isolation
  and independent of corpus order.
- v1 bodies end at signoff/signature. Phone footers, legal disclaimers, HTML
  and reply chains are Phase 6 ingestion noise layered around these bodies,
  reusing the same gold.
"""

from __future__ import annotations

import random
import re
from enum import StrEnum
from functools import lru_cache

from pydantic import BaseModel, ConfigDict

from order_desk.catalog import load_catalog
from order_desk.customers import load_customers
from order_desk.scenarios import LineItemScenario, OrderScenario


class ContractViolation(ValueError):
    """A rendered email broke a renderer contract."""


class Layout(StrEnum):
    DASH_LIST = "dash_list"
    X_LIST = "x_list"
    REVERSE_LIST = "reverse_list"
    PROSE = "prose"


class PoPlacement(StrEnum):
    SUBJECT_ONLY = "subject_only"
    BODY_ONLY = "body_only"
    BOTH = "both"


class RenderedEmail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    subject: str
    body: str
    layout: Layout
    po_placement: PoPlacement | None


GREETINGS: dict[str, tuple[str, ...]] = {
    "formal": ("Good morning,", "Hello,"),
    "casual": ("Hi,", "Hey,", "Morning,"),
    "terse": ("Hi,", ""),
}

LIST_OPENERS: dict[str, tuple[str, ...]] = {
    "formal": (
        "We would like to place the following order:",
        "Could you please arrange the following for us:",
    ),
    "casual": (
        "Can we get the following sorted please:",
        "Hoping to get another order in:",
    ),
    "terse": ("Please supply:", "Order as follows:"),
}

PROSE_OPENERS: dict[str, tuple[str, ...]] = {
    "formal": (
        "We would like to order {items}.",
        "Could you please send us {items}.",
    ),
    "casual": (
        "Could we grab {items} please?",
        "Can you send over {items}?",
    ),
    "terse": ("Please send {items}.",),
}

DATE_GLUES = (
    "Delivery {phrase} would suit us.",
    "We would need these {phrase}.",
    "Timing: {phrase}.",
)

ADDRESS_GLUES = (
    "Deliver to {addr}.",
    "Ship to: {addr}.",
    "Delivery address: {addr}.",
)

PO_GLUES = (
    "Our PO: {po}.",
    "Please book this against {po}.",
    "PO for this order: {po}.",
)

NOTE_GLUES = ("Please note: {note}.", "Just a heads up: {note}.")

PRICE_GLUES = ("@", "at")

TEAM_CLOSERS = ("Warehouse team", "The ops team", "Purchasing team")

SUBJECTS_WITH_PO = (
    "PO {po} – {company}",
    "Purchase order {po}",
    "{company} – PO {po}",
)
SUBJECTS_PLAIN = (
    "Order request – {company}",
    "New order – {company}",
    "Supplies order",
    "Restock for {company}",
)

_MASK = "\ufffd"


def _qtyless(item: LineItemScenario, *, prose: bool) -> str:
    if item.unit_surface is not None:
        return f"{item.product_surface} (usual {item.unit_surface}, qty to follow)"
    if prose:
        return f"some more {item.product_surface}"
    return f"{item.product_surface} (qty to confirm)"


def _item_line(item: LineItemScenario, layout: Layout, rng: random.Random) -> str:
    q, u, p = item.quantity_surface, item.unit_surface, item.product_surface
    if q is None:
        core = _qtyless(item, prose=layout is Layout.PROSE)
    elif layout is Layout.PROSE:
        core = f"{q} {u} of {p}" if u else f"{q} {p}"
    elif layout is Layout.X_LIST:
        core = f"{q} {u} {p}" if u else f"{q} x {p}"
    elif layout is Layout.REVERSE_LIST:
        core = f"{p} – {q} {u}" if u else f"{p} – {q}"
    else:
        core = f"{q} {u} {p}" if u else f"{q} {p}"
    if item.price_surface is not None:
        core += f" {rng.choice(PRICE_GLUES)} {item.price_surface}"
    if item.item_note is not None:
        core += f" ({item.item_note})"
    return core


def _sample_layout(n_items: int, rng: random.Random) -> Layout:
    weights = {Layout.DASH_LIST: 0.35, Layout.X_LIST: 0.2, Layout.REVERSE_LIST: 0.2}
    if n_items <= 2:
        weights[Layout.PROSE] = 0.25
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys], k=1)[0]


def render_email(scenario: OrderScenario, seed: int) -> RenderedEmail:
    rng = random.Random(f"{seed}|{scenario.scenario_id}")
    book = load_customers()
    customer = book.resolve_customer(scenario.sender_email)
    assert customer is not None, scenario.sender_email
    tone = customer.style.tone

    po = scenario.po_surface
    placement = None
    if po is not None:
        placement = rng.choices(list(PoPlacement), weights=(0.35, 0.35, 0.3), k=1)[0]

    if placement in (PoPlacement.SUBJECT_ONLY, PoPlacement.BOTH):
        subject = rng.choice(SUBJECTS_WITH_PO).format(po=po, company=customer.company)
    else:
        subject = rng.choice(SUBJECTS_PLAIN).format(company=customer.company)

    layout = _sample_layout(len(scenario.items), rng)

    lines: list[str] = []
    greeting = rng.choice(GREETINGS[tone])
    if greeting:
        lines += [greeting, ""]

    po_line = None
    if placement in (PoPlacement.BODY_ONLY, PoPlacement.BOTH):
        po_line = rng.choice(PO_GLUES).format(po=po)
    po_early = po_line is not None and rng.random() < 0.5
    if po_line is not None and po_early:
        lines += [po_line, ""]

    if layout is Layout.PROSE:
        clauses = [_item_line(item, layout, rng) for item in scenario.items]
        joined = ", ".join(clauses[:-1]) + " and " + clauses[-1] if len(clauses) > 1 else clauses[0]
        lines += [rng.choice(PROSE_OPENERS[tone]).format(items=joined), ""]
    else:
        lines += [rng.choice(LIST_OPENERS[tone]), ""]
        prefix = "" if layout is Layout.X_LIST else "- "
        lines += [prefix + _item_line(item, layout, rng) for item in scenario.items]
        lines.append("")

    if scenario.date_phrase is not None:
        lines.append(rng.choice(DATE_GLUES).format(phrase=scenario.date_phrase))
    if scenario.address_mention is not None:
        lines.append(rng.choice(ADDRESS_GLUES).format(addr=scenario.address_mention))
    if scenario.order_note is not None:
        lines.append(rng.choice(NOTE_GLUES).format(note=scenario.order_note))
    if po_line is not None and not po_early:
        lines.append(po_line)
    if lines and lines[-1] != "":
        lines.append("")

    contact = next(c for c in customer.contacts if c.email == scenario.sender_email)
    lines.append(f"{customer.style.signoff},")
    if scenario.buyer_signature is not None:
        lines.append(scenario.buyer_signature)
    elif contact.role == "shared mailbox":
        lines.append(rng.choice(TEAM_CLOSERS))

    body = "\n".join(lines).strip() + "\n"
    return RenderedEmail(
        scenario_id=scenario.scenario_id,
        subject=subject,
        body=body,
        layout=layout,
        po_placement=placement,
    )


def expected_body_surfaces(scenario: OrderScenario) -> list[str]:
    """Every label-bearing surface that must appear verbatim in the body."""
    surfaces = [
        scenario.date_phrase,
        scenario.address_mention,
        scenario.buyer_signature,
        scenario.order_note,
    ]
    for item in scenario.items:
        surfaces += [
            item.product_surface,
            item.quantity_surface,
            item.unit_surface,
            item.price_surface,
            item.item_note,
        ]
    return [s for s in surfaces if s is not None]


@lru_cache(maxsize=1)
def _term_pattern() -> re.Pattern[str]:
    catalog = load_catalog()
    terms: set[str] = set()
    for product in catalog.products:
        terms.add(product.name)
        terms.update(product.aliases)
    for canonical, aliases in catalog.units.items():
        terms.add(canonical)
        terms.update(aliases)
    ordered = sorted(terms, key=len, reverse=True)
    joined = "|".join(re.escape(term) for term in ordered)
    return re.compile(r"\b(?:" + joined + r")\b", re.IGNORECASE)


def _mask(text: str, surfaces: list[str]) -> str:
    for surface in sorted(set(surfaces), key=len, reverse=True):
        text = text.replace(surface, _MASK)
    return text


def verify_rendering(scenario: OrderScenario, rendered: RenderedEmail) -> None:
    """Raise ContractViolation unless every renderer contract holds."""
    if rendered.scenario_id != scenario.scenario_id:
        raise ContractViolation("scenario_id mismatch")

    po = scenario.po_surface
    if (po is None) != (rendered.po_placement is None):
        raise ContractViolation(f"po/placement inconsistent ({scenario.scenario_id})")
    if po is not None:
        in_subject = po in rendered.subject
        in_body = po in rendered.body
        want_subject = rendered.po_placement in (PoPlacement.SUBJECT_ONLY, PoPlacement.BOTH)
        want_body = rendered.po_placement in (PoPlacement.BODY_ONLY, PoPlacement.BOTH)
        if in_subject != want_subject or in_body != want_body:
            raise ContractViolation(
                f"po placement {rendered.po_placement} but subject={in_subject} "
                f"body={in_body} ({scenario.scenario_id})"
            )

    surfaces = expected_body_surfaces(scenario)
    everything = surfaces + ([po] if po is not None else [])

    residual = _mask(rendered.subject + "\n" + rendered.body, everything)
    if any(ch.isdigit() for ch in residual):
        raise ContractViolation(f"digit-closure broken ({scenario.scenario_id}): {residual!r}")
    match = _term_pattern().search(residual)
    if match:
        raise ContractViolation(
            f"term-closure broken by {match.group(0)!r} ({scenario.scenario_id})"
        )

    for surface in set(surfaces):
        hay = rendered.body
        shadows = [t for t in set(everything) if t != surface and surface in t]
        for shadow in sorted(shadows, key=len, reverse=True):
            hay = hay.replace(shadow, _MASK)
        if surface not in hay:
            raise ContractViolation(
                f"surface {surface!r} missing from body ({scenario.scenario_id})"
            )
