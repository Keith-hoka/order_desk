"""Order scenario generator: structured ground truth from which emails render.

The scenario, not the email text, is the source of truth. Every label-bearing
surface string -- product mentions, quantity spellings, unit words, PO
references, date phrases, addresses, signatures -- is fixed here; renderers
may only weave prose around these strings, never alter them. Gold labels are
derived from scenario facts, never back-annotated from rendered text.

Gold derivation may call the catalog resolvers: they are deterministic
oracles, not learned components, so later agreement between the runtime
validation stage and this gold is a meaningful check, not a circular one.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from order_desk.catalog import Catalog, Product, load_catalog
from order_desk.customers import CustomerBook, expand_po, load_customers
from order_desk.schemas import EmailClass, ExtractedOrder, LineItem

# Single corpus timezone is a documented v1 simplification (customers span
# NSW/VIC/QLD/SA). It keeps the clock an email presents identical to the
# clock that anchors intended_date, so relative-date gold can never drift
# from what a parser reading the email would compute. Multi-timezone is a
# v2 noise dimension.
CORPUS_TZ = ZoneInfo("Australia/Sydney")
CORPUS_EPOCH = datetime(2026, 1, 5, tzinfo=CORPUS_TZ)

NUMBER_WORDS: dict[int, str] = {6: "half a dozen", 12: "a dozen", 24: "two dozen"}

# Pack-size trap: the customer counts pieces; these words are deliberately
# absent from the unit dictionary, so the unit never resolves.
PIECE_WORDS: dict[str, str] = {
    "labels": "labels",
    "mailers": "mailers",
    "strapping": "buckles",
    "edge_protection": "boards",
    "ppe": "gloves",
}

RELATIVE_PHRASES: dict[int, str] = {
    3: "in 3 days",
    5: "in 5 days",
    7: "in a week",
    10: "in 10 days",
    14: "in a fortnight",
}

VAGUE_PHRASES = ("ASAP", "as soon as you can", "when you can")

ORDER_NOTES = (
    "tailgate required",
    "call before delivery",
    "deliver to rear dock",
    "site induction required for drivers",
)

ITEM_NOTES = (
    "brown is fine if clear is out",
    "must be the heavy duty ones",
    "same spec as our last order",
)


class MentionStyle(StrEnum):
    ALIAS = "alias"
    NAME = "name"
    SKU = "sku"


class UnitStyle(StrEnum):
    NONE = "none"
    CANONICAL = "canonical"
    ALIAS = "alias"
    PIECE = "piece"


class DateStyle(StrEnum):
    NONE = "none"
    VAGUE = "vague"
    ABSOLUTE = "absolute"
    RELATIVE_DAYS = "relative_days"


class AddressStyle(StrEnum):
    NONE = "none"
    LABEL = "label"
    FULL = "full"


class Route(StrEnum):
    TOUCHLESS = "touchless"
    CLARIFICATION = "clarification"
    EXCEPTION = "exception"


class Violation(StrEnum):
    DISCONTINUED = "discontinued"
    BELOW_MOQ = "below_moq"
    ABOVE_MAX = "above_max"
    UNRESOLVABLE_PRODUCT = "unresolvable_product"
    UNRESOLVABLE_UNIT = "unresolvable_unit"
    UNIT_MISMATCH = "unit_mismatch"


class Ask(StrEnum):
    QUANTITY = "quantity"
    DELIVERY_SITE = "delivery_site"


class ScenarioFlags(BaseModel):
    """Which noise dimensions actually fired (realized, not merely sampled)."""

    model_config = ConfigDict(extra="forbid")

    missing_po: bool = False
    missing_quantity: bool = False
    ambiguous_site: bool = False
    discontinued_item: bool = False
    qty_below_moq: bool = False
    qty_above_max: bool = False
    pack_size_trap: bool = False
    mention_typo: bool = False
    unsigned: bool = False


class LineItemScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: str  # ground-truth product, kept even when the mention is corrupted
    product_surface: str  # verbatim mention as it will appear in the email
    mention_style: MentionStyle
    typo: bool = False
    quantity_value: int | None  # gold quantity (int), None when unstated
    quantity_surface: str | None  # "72" or "a dozen"; None when unstated
    unit_surface: str | None
    unit_style: UnitStyle
    item_note: str | None = None
    intended_packs: int | None = None  # pack-size trap: how many packs are meant

    def gold(self) -> LineItem:
        return LineItem(
            product_text=self.product_surface,
            quantity=self.quantity_value,
            unit_text=self.unit_surface,
            item_notes=self.item_note,
        )


class OrderScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    email_class: Literal[EmailClass.NEW_ORDER] = EmailClass.NEW_ORDER
    customer_id: str
    sender_email: str
    sent_at: datetime
    buyer_signature: str | None  # name signed in the body; gold buyer_name_text
    po_surface: str | None
    date_style: DateStyle
    date_phrase: str | None
    intended_date: date | None  # truth for downstream date parsing
    address_style: AddressStyle
    address_mention: str | None
    address_label_truth: str | None  # which registered site is meant, if known
    order_note: str | None
    items: list[LineItemScenario] = Field(min_length=1)
    flags: ScenarioFlags

    def gold_extraction(self) -> ExtractedOrder:
        return ExtractedOrder(
            customer_po_text=self.po_surface,
            requested_date_text=self.date_phrase,
            delivery_address_text=self.address_mention,
            buyer_name_text=self.buyer_signature,
            notes=self.order_note,
            line_items=[item.gold() for item in self.items],
        )

    def expected_asks(self, book: CustomerBook) -> list[Ask]:
        customer = book.resolve_customer(self.sender_email)
        assert customer is not None
        asks: list[Ask] = []
        if any(item.quantity_value is None for item in self.items):
            asks.append(Ask.QUANTITY)
        if self.address_mention is None and len(customer.delivery_addresses) > 1:
            asks.append(Ask.DELIVERY_SITE)
        return asks

    def expected_violations(self, catalog: Catalog) -> list[Violation]:
        """One entry per offending check per line item; duplicates possible."""
        out: list[Violation] = []
        for item in self.items:
            product = catalog.resolve_sku(item.product_surface)
            if product is None:
                out.append(Violation.UNRESOLVABLE_PRODUCT)
                continue
            if not product.active:
                out.append(Violation.DISCONTINUED)
            if item.quantity_value is not None:
                if item.quantity_value < product.moq:
                    out.append(Violation.BELOW_MOQ)
                elif item.quantity_value > product.max_qty:
                    out.append(Violation.ABOVE_MAX)
            if item.unit_surface is not None:
                unit = catalog.resolve_unit(item.unit_surface)
                if unit is None:
                    out.append(Violation.UNRESOLVABLE_UNIT)
                elif unit != product.unit:
                    out.append(Violation.UNIT_MISMATCH)
        return out

    def expected_route(self, catalog: Catalog, book: CustomerBook) -> Route:
        if self.expected_violations(catalog):
            return Route.EXCEPTION
        if self.expected_asks(book):
            return Route.CLARIFICATION
        return Route.TOUCHLESS


class GeneratorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_count_weights: dict[int, float] = {1: 0.3, 2: 0.3, 3: 0.25, 4: 0.1, 5: 0.05}
    mention_style_weights: dict[MentionStyle, float] = {
        MentionStyle.ALIAS: 0.55,
        MentionStyle.NAME: 0.3,
        MentionStyle.SKU: 0.15,
    }
    unit_style_weights: dict[UnitStyle, float] = {
        UnitStyle.NONE: 0.25,
        UnitStyle.CANONICAL: 0.35,
        UnitStyle.ALIAS: 0.4,
    }
    date_style_weights: dict[DateStyle, float] = {
        DateStyle.NONE: 0.15,
        DateStyle.VAGUE: 0.15,
        DateStyle.ABSOLUTE: 0.4,
        DateStyle.RELATIVE_DAYS: 0.3,
    }
    address_style_weights: dict[AddressStyle, float] = {
        AddressStyle.NONE: 0.4,
        AddressStyle.LABEL: 0.3,
        AddressStyle.FULL: 0.3,
    }
    p_missing_po: float = 0.15
    p_missing_quantity: float = 0.12
    p_pack_size_trap: float = 0.12
    p_discontinued: float = 0.06
    p_below_moq: float = 0.05
    p_above_max: float = 0.05
    p_mention_typo: float = 0.08
    p_number_word: float = 0.5
    p_item_note: float = 0.15
    p_order_note: float = 0.25
    p_unsigned_personal: float = 0.1
    p_signed_shared: float = 0.6


def _weighted[T](rng: random.Random, weights: dict[T, float]) -> T:
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys], k=1)[0]


def _transpose(text: str, rng: random.Random) -> str:
    spots = [
        i
        for i in range(len(text) - 1)
        if text[i].isalpha() and text[i + 1].isalpha() and text[i] != text[i + 1]
    ]
    if not spots:
        return text
    i = rng.choice(spots)
    return text[:i] + text[i + 1] + text[i] + text[i + 2 :]


def _sample_sent_at(rng: random.Random) -> datetime:
    return CORPUS_EPOCH + timedelta(
        days=rng.randint(0, 180), hours=rng.randint(7, 17), minutes=rng.randint(0, 59)
    )


def _sample_quantity(product: Product, rng: random.Random) -> int:
    return min(product.moq * rng.choice((1, 2, 3, 4, 6, 8, 10)), product.max_qty)


def _mention(product: Product, style: MentionStyle, rng: random.Random) -> str:
    if style is MentionStyle.ALIAS:
        return rng.choice(product.aliases)
    if style is MentionStyle.NAME:
        return product.name
    return product.sku


def _unit_surface(
    product: Product, style: UnitStyle, catalog: Catalog, rng: random.Random
) -> str | None:
    if style is UnitStyle.NONE:
        return None
    if style is UnitStyle.CANONICAL:
        return product.unit
    return rng.choice(catalog.units[product.unit])


def _normal_item(
    product: Product,
    catalog: Catalog,
    rng: random.Random,
    config: GeneratorConfig,
    *,
    typo: bool,
    omit_quantity: bool,
    force_quantity: int | None,
) -> LineItemScenario:
    style = MentionStyle.ALIAS if typo else _weighted(rng, config.mention_style_weights)
    surface = _mention(product, style, rng)
    realized_typo = False
    if typo:
        for _ in range(5):
            candidate = _transpose(surface, rng)
            if catalog.resolve_sku(candidate) is None:
                surface, realized_typo = candidate, True
                break
    if omit_quantity:
        quantity_value: int | None = None
        quantity_surface: str | None = None
    else:
        quantity_value = (
            force_quantity if force_quantity is not None else _sample_quantity(product, rng)
        )
        word = NUMBER_WORDS.get(quantity_value)
        use_word = word is not None and rng.random() < config.p_number_word
        quantity_surface = word if use_word else str(quantity_value)
    unit_style = _weighted(rng, config.unit_style_weights)
    return LineItemScenario(
        sku=product.sku,
        product_surface=surface,
        mention_style=style,
        typo=realized_typo,
        quantity_value=quantity_value,
        quantity_surface=quantity_surface,
        unit_surface=_unit_surface(product, unit_style, catalog, rng),
        unit_style=unit_style,
        item_note=rng.choice(ITEM_NOTES) if rng.random() < config.p_item_note else None,
        intended_packs=None,
    )


def _trap_item(product: Product, rng: random.Random) -> LineItemScenario:
    assert product.pack_size is not None
    packs = rng.randint(1, 4)
    quantity = product.pack_size * packs
    return LineItemScenario(
        sku=product.sku,
        product_surface=rng.choice(product.aliases),
        mention_style=MentionStyle.ALIAS,
        typo=False,
        quantity_value=quantity,
        quantity_surface=str(quantity),
        unit_surface=PIECE_WORDS[product.category],
        unit_style=UnitStyle.PIECE,
        item_note=None,
        intended_packs=packs,
    )


def _sample_scenario(
    index: int,
    rng: random.Random,
    catalog: Catalog,
    book: CustomerBook,
    config: GeneratorConfig,
) -> OrderScenario:
    customer = rng.choice(book.customers)
    contact = rng.choice(customer.contacts)
    sent_at = _sample_sent_at(rng)

    personal_first_names = [
        c.name.split()[0] for c in customer.contacts if c.role != "shared mailbox"
    ]
    if contact.role == "shared mailbox":
        signed = bool(personal_first_names) and rng.random() < config.p_signed_shared
        signature = rng.choice(personal_first_names) if signed else None
    else:
        signature = None if rng.random() < config.p_unsigned_personal else contact.name.split()[0]

    if customer.po_template is None:
        po_surface, missing_po = None, False
    elif rng.random() < config.p_missing_po:
        po_surface, missing_po = None, True
    else:
        po_surface, missing_po = expand_po(customer.po_template, rng), False

    date_style = _weighted(rng, config.date_style_weights)
    if date_style is DateStyle.NONE:
        date_phrase, intended_date = None, None
    elif date_style is DateStyle.VAGUE:
        date_phrase, intended_date = rng.choice(VAGUE_PHRASES), None
    elif date_style is DateStyle.ABSOLUTE:
        intended_date = sent_at.date() + timedelta(days=rng.randint(3, 14))
        date_phrase = f"{intended_date.day} {intended_date:%B}"
    else:
        days = rng.choice(tuple(RELATIVE_PHRASES))
        intended_date = sent_at.date() + timedelta(days=days)
        date_phrase = RELATIVE_PHRASES[days]

    address_style = _weighted(rng, config.address_style_weights)
    if address_style is AddressStyle.NONE:
        address_mention = None
        address_label_truth = (
            customer.delivery_addresses[0].label if len(customer.delivery_addresses) == 1 else None
        )
    else:
        addr = rng.choice(customer.delivery_addresses)
        address_label_truth = addr.label
        if address_style is AddressStyle.LABEL:
            address_mention = addr.label
        else:
            parts = [addr.line1]
            if addr.line2:
                parts.append(addr.line2)
            parts.append(f"{addr.suburb} {addr.state} {addr.postcode}")
            address_mention = ", ".join(parts)

    want_trap = rng.random() < config.p_pack_size_trap
    want_discontinued = rng.random() < config.p_discontinued
    want_below = rng.random() < config.p_below_moq
    want_above = not want_below and rng.random() < config.p_above_max
    want_missing_qty = rng.random() < config.p_missing_quantity
    want_typo = rng.random() < config.p_mention_typo

    n_items = _weighted(rng, config.item_count_weights)
    actives = catalog.active_products
    trap_product: Product | None = None
    if want_trap:
        eligible = [p for p in actives if p.pack_size is not None and p.category in PIECE_WORDS]
        trap_product = rng.choice(eligible)
    normal_pool = [p for p in actives if trap_product is None or p.sku != trap_product.sku]
    normal_products = rng.sample(normal_pool, k=max(n_items - (1 if trap_product else 0), 0))

    oor_product: Product | None = None
    oor_quantity: int | None = None
    if want_below:
        candidates = [p for p in normal_products if p.moq >= 2]
        if candidates:
            oor_product = rng.choice(candidates)
            oor_quantity = rng.randint(1, oor_product.moq - 1)
    elif want_above and normal_products:
        oor_product = rng.choice(normal_products)
        oor_quantity = oor_product.max_qty + oor_product.moq * rng.choice((1, 2, 4))

    typo_product: Product | None = None
    if want_typo:
        candidates = [p for p in normal_products if p is not oor_product] or normal_products
        if candidates:
            typo_product = rng.choice(candidates)

    missing_product: Product | None = None
    if want_missing_qty:
        candidates = [p for p in normal_products if p is not oor_product]
        if candidates:
            missing_product = rng.choice(candidates)

    items = [
        _normal_item(
            product,
            catalog,
            rng,
            config,
            typo=product is typo_product,
            omit_quantity=product is missing_product,
            force_quantity=oor_quantity if product is oor_product else None,
        )
        for product in normal_products
    ]
    if trap_product is not None:
        items.append(_trap_item(trap_product, rng))
    if want_discontinued:
        inactive = [p for p in catalog.products if not p.active]
        items.append(
            _normal_item(
                rng.choice(inactive),
                catalog,
                rng,
                config,
                typo=False,
                omit_quantity=False,
                force_quantity=None,
            )
        )
    rng.shuffle(items)

    flags = ScenarioFlags(
        missing_po=missing_po,
        missing_quantity=any(item.quantity_value is None for item in items),
        ambiguous_site=address_mention is None and len(customer.delivery_addresses) > 1,
        discontinued_item=want_discontinued,
        qty_below_moq=want_below and oor_product is not None,
        qty_above_max=want_above and oor_product is not None,
        pack_size_trap=trap_product is not None,
        mention_typo=any(item.typo for item in items),
        unsigned=signature is None,
    )

    return OrderScenario(
        scenario_id=f"SCN-{index:06d}",
        customer_id=customer.customer_id,
        sender_email=contact.email,
        sent_at=sent_at,
        buyer_signature=signature,
        po_surface=po_surface,
        date_style=date_style,
        date_phrase=date_phrase,
        intended_date=intended_date,
        address_style=address_style,
        address_mention=address_mention,
        address_label_truth=address_label_truth,
        order_note=rng.choice(ORDER_NOTES) if rng.random() < config.p_order_note else None,
        items=items,
        flags=flags,
    )


def generate_scenarios(
    n: int, seed: int, config: GeneratorConfig | None = None
) -> list[OrderScenario]:
    """Deterministically generate n new-order scenarios for a given seed."""
    catalog, book = load_catalog(), load_customers()
    cfg = config or GeneratorConfig()
    rng = random.Random(seed)
    return [_sample_scenario(i, rng, catalog, book, cfg) for i in range(n)]
