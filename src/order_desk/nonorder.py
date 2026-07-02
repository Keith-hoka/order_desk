"""Non-order email classes: amendment, cancellation, inquiry, other.

Contract matrix (locked in step 1.6):
- amendment: full contracts -- surface containment, digit-closure, term-closure.
- cancellation: closures, plus containment of the PO or temporal reference.
- inquiry: exempt from closures (quote lookalikes mention products and
  quantities by design); the machine contract is a class-marker check.
- other: light contract -- must never match any customer's PO pattern; sender
  domain rules (misdirected = known customer, marketing/courier = unknown).

v1 simplifications, recorded for the corpus notes: one change per amendment,
amendment lines carry no noise dimensions (no typo/trap/price), and amendment
PO references are generated from the customer's template without linking to a
concrete order in the corpus -- cross-record references would leak across
train/test splits.
"""

from __future__ import annotations

import random
import re
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from order_desk.catalog import load_catalog
from order_desk.customers import Contact, Customer, expand_po, load_customers, po_regex
from order_desk.renderer import (
    GREETINGS,
    TEAM_CLOSERS,
    ContractViolation,
    _mask,
    _term_pattern,
)
from order_desk.scenarios import (
    RELATIVE_PHRASES,
    LineItemScenario,
    MentionStyle,
    UnitStyle,
    _sample_quantity,
    _sample_sent_at,
)
from order_desk.schemas import EmailClass, ExtractedOrder


class RenderedMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    subject: str
    body: str


# ---------------------------------------------------------------- shared bits


def _signature(customer: Customer, contact: Contact, rng: random.Random) -> str | None:
    """Mirrors the order generator's signing behaviour (scenarios module)."""
    personal = [c.name.split()[0] for c in customer.contacts if c.role != "shared mailbox"]
    if contact.role == "shared mailbox":
        if personal and rng.random() < 0.6:
            return rng.choice(personal)
        return None
    return None if rng.random() < 0.1 else contact.name.split()[0]


def _greeting_lines(tone: str, rng: random.Random) -> list[str]:
    greeting = rng.choice(GREETINGS[tone])
    return [greeting, ""] if greeting else []


def _closing_lines(
    customer: Customer, contact: Contact, signature: str | None, rng: random.Random
) -> list[str]:
    lines = [f"{customer.style.signoff},"]
    if signature is not None:
        lines.append(signature)
    elif contact.role == "shared mailbox":
        lines.append(rng.choice(TEAM_CLOSERS))
    return lines


def _finish(scenario_id: str, subject: str, lines: list[str]) -> RenderedMessage:
    return RenderedMessage(
        scenario_id=scenario_id, subject=subject, body="\n".join(lines).strip() + "\n"
    )


def _verify_id(scenario_id: str, rendered: RenderedMessage) -> None:
    if rendered.scenario_id != scenario_id:
        raise ContractViolation("scenario_id mismatch")


def _verify_containment(body: str, surfaces: list[str], scenario_id: str) -> None:
    pool = set(surfaces)
    for surface in pool:
        hay = body
        shadows = [t for t in pool if t != surface and surface in t]
        for shadow in sorted(shadows, key=len, reverse=True):
            hay = hay.replace(shadow, "\ufffd")
        if surface not in hay:
            raise ContractViolation(f"surface {surface!r} missing from body ({scenario_id})")


def _verify_closures(subject: str, body: str, surfaces: list[str], scenario_id: str) -> None:
    residual = _mask(subject + "\n" + body, surfaces)
    if any(ch.isdigit() for ch in residual):
        raise ContractViolation(f"digit-closure broken ({scenario_id}): {residual!r}")
    match = _term_pattern().search(residual)
    if match:
        raise ContractViolation(f"term-closure broken by {match.group(0)!r} ({scenario_id})")


TEMPORAL_REFS = (
    "yesterday's order",
    "the order we placed this morning",
    "our order from Monday",
)

# ------------------------------------------------------------------ amendment


class AmendmentChange(StrEnum):
    QTY_CHANGE = "qty_change"
    ADD_ITEM = "add_item"
    REMOVE_ITEM = "remove_item"
    DATE_CHANGE = "date_change"


class AmendmentScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    email_class: Literal[EmailClass.AMENDMENT] = EmailClass.AMENDMENT
    customer_id: str
    sender_email: str
    sent_at: datetime
    buyer_signature: str | None
    referenced_po: str | None
    temporal_ref: str | None
    change_type: AmendmentChange
    line: LineItemScenario | None
    date_phrase: str | None
    intended_date: date | None

    @model_validator(mode="after")
    def integrity(self) -> AmendmentScenario:
        if (self.referenced_po is None) == (self.temporal_ref is None):
            raise ValueError("exactly one of referenced_po/temporal_ref must be set")
        if self.change_type is AmendmentChange.DATE_CHANGE:
            if self.line is not None or self.date_phrase is None or self.intended_date is None:
                raise ValueError("date change carries a date, not a line")
        else:
            if self.line is None or self.date_phrase is not None or self.intended_date is not None:
                raise ValueError("item change carries a line, not a date")
            if self.change_type is AmendmentChange.REMOVE_ITEM:
                if self.line.quantity_value is not None or self.line.unit_surface is not None:
                    raise ValueError("removal lines carry no quantity or unit")
            elif self.line.quantity_value is None:
                raise ValueError("qty/add lines carry a quantity")
        return self

    def gold_extraction(self) -> ExtractedOrder:
        return ExtractedOrder(
            customer_po_text=self.referenced_po,
            requested_date_text=self.date_phrase,
            delivery_address_text=None,
            buyer_name_text=self.buyer_signature,
            notes=None,
            line_items=[self.line.gold()] if self.line is not None else [],
        )


def generate_amendments(n: int, seed: int) -> list[AmendmentScenario]:
    catalog, book = load_catalog(), load_customers()
    rng = random.Random(f"{seed}|amendment")
    out: list[AmendmentScenario] = []
    for i in range(n):
        customer = rng.choice(book.customers)
        contact = rng.choice(customer.contacts)
        sent_at = _sample_sent_at(rng)
        signature = _signature(customer, contact, rng)
        if customer.po_template is not None:
            referenced_po, temporal = expand_po(customer.po_template, rng), None
        else:
            referenced_po, temporal = None, rng.choice(TEMPORAL_REFS)

        change = rng.choice(list(AmendmentChange))
        line: LineItemScenario | None = None
        date_phrase: str | None = None
        intended: date | None = None
        if change is AmendmentChange.DATE_CHANGE:
            if rng.random() < 0.5:
                intended = sent_at.date() + timedelta(days=rng.randint(3, 14))
                date_phrase = f"{intended.day} {intended:%B}"
            else:
                days = rng.choice(tuple(RELATIVE_PHRASES))
                intended = sent_at.date() + timedelta(days=days)
                date_phrase = RELATIVE_PHRASES[days]
        else:
            product = rng.choice(catalog.active_products)
            style = rng.choices(list(MentionStyle), weights=(0.6, 0.25, 0.15), k=1)[0]
            if style is MentionStyle.SKU:
                surface = product.sku
            elif style is MentionStyle.NAME:
                surface = product.name
            else:
                surface = rng.choice(product.aliases)
            if change is AmendmentChange.REMOVE_ITEM:
                line = LineItemScenario(
                    sku=product.sku,
                    product_surface=surface,
                    mention_style=style,
                    typo=False,
                    quantity_value=None,
                    quantity_surface=None,
                    unit_surface=None,
                    unit_style=UnitStyle.NONE,
                    item_note=None,
                    price_cents=None,
                    price_surface=None,
                    intended_packs=None,
                )
            else:
                qty = _sample_quantity(product, rng)
                unit_style = rng.choices(
                    (UnitStyle.NONE, UnitStyle.CANONICAL, UnitStyle.ALIAS),
                    weights=(0.3, 0.25, 0.45),
                    k=1,
                )[0]
                if unit_style is UnitStyle.NONE:
                    unit = None
                elif unit_style is UnitStyle.CANONICAL:
                    unit = product.unit
                else:
                    unit = rng.choice(catalog.units[product.unit])
                line = LineItemScenario(
                    sku=product.sku,
                    product_surface=surface,
                    mention_style=style,
                    typo=False,
                    quantity_value=qty,
                    quantity_surface=str(qty),
                    unit_surface=unit,
                    unit_style=unit_style,
                    item_note=None,
                    price_cents=None,
                    price_surface=None,
                    intended_packs=None,
                )

        out.append(
            AmendmentScenario(
                scenario_id=f"AMD-{i:06d}",
                customer_id=customer.customer_id,
                sender_email=contact.email,
                sent_at=sent_at,
                buyer_signature=signature,
                referenced_po=referenced_po,
                temporal_ref=temporal,
                change_type=change,
                line=line,
                date_phrase=date_phrase,
                intended_date=intended,
            )
        )
    return out


AMEND_SUBJECTS = ("Change to our order", "Order amendment – {company}", "Amendment to recent order")
AMEND_REF_GLUES_PO = ("Regarding PO {po} –", "Re our PO {po}:", "Quick change to PO {po}:")
AMEND_REF_GLUES_TEMPORAL = ("Regarding {ref} –", "About {ref}:", "Quick change to {ref}:")
QTY_GLUES_WITH_UNIT = (
    "could we make the {p} {q} {u} instead?",
    "please change the {p} to {q} {u}.",
)
QTY_GLUES_NO_UNIT = (
    "could we make the {p} {q} instead?",
    "please bump the {p} to {q}.",
)
ADD_GLUES_WITH_UNIT = (
    "could you also add {q} {u} of {p} to it?",
    "please add {q} {u} of {p} as well.",
)
ADD_GLUES_NO_UNIT = (
    "could you also add {q} {p} to it?",
    "please add {q} more {p} as well.",
)
REMOVE_GLUES = (
    "please drop the {p} from it.",
    "we no longer need the {p} – please take it off.",
)
DATE_CHANGE_GLUES = (
    "delivery {phrase} would suit us better.",
    "sorry for the change – delivery {phrase} works better for us.",
)


def _change_sentence(scenario: AmendmentScenario, rng: random.Random) -> str:
    if scenario.change_type is AmendmentChange.DATE_CHANGE:
        return rng.choice(DATE_CHANGE_GLUES).format(phrase=scenario.date_phrase)
    line = scenario.line
    assert line is not None
    if scenario.change_type is AmendmentChange.REMOVE_ITEM:
        return rng.choice(REMOVE_GLUES).format(p=line.product_surface)
    if line.unit_surface is not None:
        pool = (
            QTY_GLUES_WITH_UNIT
            if scenario.change_type is AmendmentChange.QTY_CHANGE
            else ADD_GLUES_WITH_UNIT
        )
        return rng.choice(pool).format(
            p=line.product_surface, q=line.quantity_surface, u=line.unit_surface
        )
    pool = (
        QTY_GLUES_NO_UNIT
        if scenario.change_type is AmendmentChange.QTY_CHANGE
        else ADD_GLUES_NO_UNIT
    )
    return rng.choice(pool).format(p=line.product_surface, q=line.quantity_surface)


def render_amendment(scenario: AmendmentScenario, seed: int) -> RenderedMessage:
    rng = random.Random(f"{seed}|{scenario.scenario_id}")
    book = load_customers()
    customer = book.resolve_customer(scenario.sender_email)
    assert customer is not None, scenario.sender_email
    contact = next(c for c in customer.contacts if c.email == scenario.sender_email)

    subject = rng.choice(AMEND_SUBJECTS).format(company=customer.company)
    if scenario.referenced_po is not None:
        ref = rng.choice(AMEND_REF_GLUES_PO).format(po=scenario.referenced_po)
    else:
        ref = rng.choice(AMEND_REF_GLUES_TEMPORAL).format(ref=scenario.temporal_ref)

    lines = _greeting_lines(customer.style.tone, rng)
    lines += [f"{ref} {_change_sentence(scenario, rng)}", ""]
    lines += _closing_lines(customer, contact, scenario.buyer_signature, rng)
    return _finish(scenario.scenario_id, subject, lines)


def verify_amendment(scenario: AmendmentScenario, rendered: RenderedMessage) -> None:
    _verify_id(scenario.scenario_id, rendered)
    maybe = [
        scenario.referenced_po,
        scenario.temporal_ref,
        scenario.date_phrase,
        scenario.buyer_signature,
    ]
    if scenario.line is not None:
        maybe += [
            scenario.line.product_surface,
            scenario.line.quantity_surface,
            scenario.line.unit_surface,
        ]
    surfaces = [s for s in maybe if s is not None]
    _verify_containment(rendered.body, surfaces, scenario.scenario_id)
    _verify_closures(rendered.subject, rendered.body, surfaces, scenario.scenario_id)


# --------------------------------------------------------------- cancellation


class CancellationScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    email_class: Literal[EmailClass.CANCELLATION] = EmailClass.CANCELLATION
    customer_id: str
    sender_email: str
    sent_at: datetime
    buyer_signature: str | None
    referenced_po: str | None
    temporal_ref: str | None

    @model_validator(mode="after")
    def integrity(self) -> CancellationScenario:
        if (self.referenced_po is None) == (self.temporal_ref is None):
            raise ValueError("exactly one of referenced_po/temporal_ref must be set")
        return self


def generate_cancellations(n: int, seed: int) -> list[CancellationScenario]:
    book = load_customers()
    rng = random.Random(f"{seed}|cancellation")
    out: list[CancellationScenario] = []
    for i in range(n):
        customer = rng.choice(book.customers)
        contact = rng.choice(customer.contacts)
        if customer.po_template is not None and rng.random() < 0.75:
            referenced_po, temporal = expand_po(customer.po_template, rng), None
        else:
            referenced_po, temporal = None, rng.choice(TEMPORAL_REFS)
        out.append(
            CancellationScenario(
                scenario_id=f"CXL-{i:06d}",
                customer_id=customer.customer_id,
                sender_email=contact.email,
                sent_at=_sample_sent_at(rng),
                buyer_signature=_signature(customer, contact, rng),
                referenced_po=referenced_po,
                temporal_ref=temporal,
            )
        )
    return out


CANCEL_SUBJECTS = ("Order cancellation", "Cancellation – {company}", "Please cancel our order")
CANCEL_GLUES_PO = (
    "Please cancel PO {po}.",
    "Could you cancel PO {po} for us?",
    "We need to cancel PO {po}.",
)
CANCEL_GLUES_TEMPORAL = (
    "Please cancel {ref}.",
    "Could you cancel {ref} for us?",
    "We need to cancel {ref}.",
)
CANCEL_APOLOGIES = (
    "Apologies for the mess-around.",
    "Sorry for the hassle.",
    "It was raised in error.",
)


def render_cancellation(scenario: CancellationScenario, seed: int) -> RenderedMessage:
    rng = random.Random(f"{seed}|{scenario.scenario_id}")
    book = load_customers()
    customer = book.resolve_customer(scenario.sender_email)
    assert customer is not None, scenario.sender_email
    contact = next(c for c in customer.contacts if c.email == scenario.sender_email)

    subject = rng.choice(CANCEL_SUBJECTS).format(company=customer.company)
    if scenario.referenced_po is not None:
        ask = rng.choice(CANCEL_GLUES_PO).format(po=scenario.referenced_po)
    else:
        ask = rng.choice(CANCEL_GLUES_TEMPORAL).format(ref=scenario.temporal_ref)
    if rng.random() < 0.4:
        ask += " " + rng.choice(CANCEL_APOLOGIES)

    lines = _greeting_lines(customer.style.tone, rng) + [ask, ""]
    lines += _closing_lines(customer, contact, scenario.buyer_signature, rng)
    return _finish(scenario.scenario_id, subject, lines)


def verify_cancellation(scenario: CancellationScenario, rendered: RenderedMessage) -> None:
    _verify_id(scenario.scenario_id, rendered)
    maybe = [scenario.referenced_po, scenario.temporal_ref, scenario.buyer_signature]
    surfaces = [s for s in maybe if s is not None]
    _verify_containment(rendered.body, surfaces, scenario.scenario_id)
    _verify_closures(rendered.subject, rendered.body, surfaces, scenario.scenario_id)


# -------------------------------------------------------------------- inquiry


class InquiryType(StrEnum):
    QUOTE_REQUEST = "quote_request"
    STOCK_CHECK = "stock_check"
    GENERAL = "general"


class InquiryScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    email_class: Literal[EmailClass.INQUIRY] = EmailClass.INQUIRY
    customer_id: str
    sender_email: str
    sent_at: datetime
    buyer_signature: str | None
    inquiry_type: InquiryType


def generate_inquiries(n: int, seed: int) -> list[InquiryScenario]:
    book = load_customers()
    rng = random.Random(f"{seed}|inquiry")
    out: list[InquiryScenario] = []
    for i in range(n):
        customer = rng.choice(book.customers)
        contact = rng.choice(customer.contacts)
        out.append(
            InquiryScenario(
                scenario_id=f"INQ-{i:06d}",
                customer_id=customer.customer_id,
                sender_email=contact.email,
                sent_at=_sample_sent_at(rng),
                buyer_signature=_signature(customer, contact, rng),
                inquiry_type=rng.choice(list(InquiryType)),
            )
        )
    return out


INQUIRY_MARKERS = re.compile(
    r"\?|quote|pricing|price list|lead time|in stock|availability|catalogue", re.IGNORECASE
)
QUOTE_SUBJECTS = ("Quote request", "Pricing request")
QUOTE_OPENERS = ("Could you put together a quote for:", "Can we get pricing on the following:")
QUOTE_CLOSERS = ("Any volume pricing would be good to know.", "Keen to see where the numbers land.")
STOCK_TEMPLATES = (
    "Do you have {p} in stock at the moment? What sort of lead time are we looking at?",
    "Quick one – is {p} available right now, and how fast could you get it to us?",
)
GENERAL_TEMPLATES = (
    "Could you send through your latest product catalogue?",
    "What is your cutoff for same day dispatch?",
    "Who is the best person to talk to about account pricing?",
    "Do you deliver to regional Queensland, and how does freight get charged?",
)
GENERAL_SUBJECTS = ("Quick question", "Question about supply")


def render_inquiry(scenario: InquiryScenario, seed: int) -> RenderedMessage:
    rng = random.Random(f"{seed}|{scenario.scenario_id}")
    catalog, book = load_catalog(), load_customers()
    customer = book.resolve_customer(scenario.sender_email)
    assert customer is not None, scenario.sender_email
    contact = next(c for c in customer.contacts if c.email == scenario.sender_email)

    lines = _greeting_lines(customer.style.tone, rng)
    if scenario.inquiry_type is InquiryType.QUOTE_REQUEST:
        subject = rng.choice(QUOTE_SUBJECTS)
        products = rng.sample(catalog.active_products, k=rng.randint(1, 3))
        lines += [rng.choice(QUOTE_OPENERS), ""]
        lines += [f"- {_sample_quantity(p, rng)} x {rng.choice(p.aliases)}" for p in products]
        lines += ["", rng.choice(QUOTE_CLOSERS), ""]
    elif scenario.inquiry_type is InquiryType.STOCK_CHECK:
        subject = "Stock query"
        product = rng.choice(catalog.active_products)
        lines += [rng.choice(STOCK_TEMPLATES).format(p=rng.choice(product.aliases)), ""]
    else:
        subject = rng.choice(GENERAL_SUBJECTS)
        lines += [rng.choice(GENERAL_TEMPLATES), ""]
    lines += _closing_lines(customer, contact, scenario.buyer_signature, rng)
    return _finish(scenario.scenario_id, subject, lines)


def verify_inquiry(scenario: InquiryScenario, rendered: RenderedMessage) -> None:
    _verify_id(scenario.scenario_id, rendered)
    if not INQUIRY_MARKERS.search(rendered.subject + "\n" + rendered.body):
        raise ContractViolation(f"inquiry lacks class markers ({scenario.scenario_id})")


# ---------------------------------------------------------------------- other


class OtherType(StrEnum):
    VENDOR_MARKETING = "vendor_marketing"
    MISDIRECTED = "misdirected"
    COURIER_NOTICE = "courier_notice"


class OtherScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    email_class: Literal[EmailClass.OTHER] = EmailClass.OTHER
    other_type: OtherType
    sender_name: str
    sender_email: str
    customer_id: str | None
    sent_at: datetime


MARKETING_SENDERS = (
    ("Talia Reyes", "talia@brightreach-media.com"),
    ("Apex Growth Team", "hello@apexgrowthpartners.com"),
)
COURIER_SENDERS = (
    ("FastTrack Freight", "noreply@fasttrackfreight.com.au"),
    ("Linehaul Express", "tracking@linehaulexpress.com.au"),
)


def generate_others(n: int, seed: int) -> list[OtherScenario]:
    book = load_customers()
    rng = random.Random(f"{seed}|other")
    out: list[OtherScenario] = []
    for i in range(n):
        other_type = rng.choice(list(OtherType))
        if other_type is OtherType.MISDIRECTED:
            customer = rng.choice(book.customers)
            personal = [c for c in customer.contacts if c.role != "shared mailbox"]
            contact = rng.choice(personal)
            name, email, customer_id = contact.name, contact.email, customer.customer_id
        else:
            pool = (
                MARKETING_SENDERS if other_type is OtherType.VENDOR_MARKETING else COURIER_SENDERS
            )
            name, email = rng.choice(pool)
            assert book.resolve_customer(email) is None, email
            customer_id = None
        out.append(
            OtherScenario(
                scenario_id=f"OTH-{i:06d}",
                other_type=other_type,
                sender_name=name,
                sender_email=email,
                customer_id=customer_id,
                sent_at=_sample_sent_at(rng),
            )
        )
    return out


MARKETING_SUBJECTS = ("Grow your wholesale pipeline", "A quick idea for your business")
MARKETING_BODY = (
    "Hi there,\n\n"
    "We help suppliers like you win more repeat business online. Our team has "
    "run campaigns for over 300 Australian companies this year alone.\n\n"
    "Would you be open to a free 15 minute chat this week?\n\n"
    "Best,\n{name}"
)
COURIER_BODY = (
    "Your consignment {cns} is booked for delivery today between 9am and 1pm.\n"
    "No signature is required for this delivery.\n\n{name}"
)
MISDIRECTED_SUBJECTS = ("Toolbox meeting", "Thursday meeting")
MISDIRECTED_BODY = (
    "Hi Sarah,\n\n"
    "Just confirming Thursday's toolbox meeting has moved to the lunchroom. "
    "Can you let your crew know before knock-off?\n\n{signoff},\n{first}"
)


def render_other(scenario: OtherScenario, seed: int) -> RenderedMessage:
    rng = random.Random(f"{seed}|{scenario.scenario_id}")
    if scenario.other_type is OtherType.VENDOR_MARKETING:
        subject = rng.choice(MARKETING_SUBJECTS)
        body = MARKETING_BODY.format(name=scenario.sender_name)
    elif scenario.other_type is OtherType.COURIER_NOTICE:
        cns = f"CNS-9{rng.randint(10000, 99999)}"
        subject = f"Delivery update – consignment {cns}"
        body = COURIER_BODY.format(cns=cns, name=scenario.sender_name)
    else:
        book = load_customers()
        customer = book.resolve_customer(scenario.sender_email)
        assert customer is not None, scenario.sender_email
        subject = rng.choice(MISDIRECTED_SUBJECTS)
        body = MISDIRECTED_BODY.format(
            signoff=customer.style.signoff, first=scenario.sender_name.split()[0]
        )
    return RenderedMessage(scenario_id=scenario.scenario_id, subject=subject, body=body)


def verify_other(scenario: OtherScenario, rendered: RenderedMessage) -> None:
    _verify_id(scenario.scenario_id, rendered)
    text = rendered.subject + "\n" + rendered.body
    book = load_customers()
    for customer in book.customers:
        if customer.po_template is None:
            continue
        if po_regex(customer.po_template).search(text):
            raise ContractViolation(
                f"other email matches {customer.customer_id} PO pattern ({scenario.scenario_id})"
            )
    sender = book.resolve_customer(scenario.sender_email)
    if scenario.other_type is OtherType.MISDIRECTED:
        if sender is None:
            raise ContractViolation("misdirected email must come from a known customer")
    elif sender is not None:
        raise ContractViolation("marketing/courier email must come from an unknown domain")
