"""Canonical extraction schema: the contract between corpus, model, and validation.

Field descriptions double as model-facing instructions -- the JSON schema is
rendered into the extraction prompt, so editing a description edits the prompt.
The committed snapshot under tests/snapshots/ gates any drift through CI.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EmailClass(StrEnum):
    """Classification labels for inbound emails (SPEC section 1, stage 2)."""

    NEW_ORDER = "new_order"
    AMENDMENT = "amendment"
    CANCELLATION = "cancellation"
    INQUIRY = "inquiry"
    OTHER = "other"


class LineItem(BaseModel):
    """A single ordered product as expressed in the email."""

    model_config = ConfigDict(extra="forbid", strict=True)

    product_text: str = Field(
        min_length=1,
        description=(
            "The product exactly as the customer wrote it, verbatim. "
            "Never map it to a catalog name or product code."
        ),
    )
    quantity: int | None = Field(
        ge=1,
        description=(
            "The quantity as an integer. Convert number words such as twelve or "
            "a dozen to digits. Use null if no quantity is stated; never guess."
        ),
    )
    unit_text: str | None = Field(
        min_length=1,
        description=(
            "The unit word exactly as written, e.g. rolls, ctns, boxes. Use null if none is given."
        ),
    )
    unit_price_text: str | None = Field(
        min_length=1,
        description=(
            "The per-unit price exactly as the customer wrote it, including "
            "the currency symbol, e.g. $7.80. Use null if no price is stated "
            "for this item."
        ),
    )
    item_notes: str | None = Field(
        min_length=1,
        description="Instructions specific to this line item, verbatim. Use null if none.",
    )


class ExtractedOrder(BaseModel):
    """Structured purchase order extracted from one customer email.

    Every key is required. Use null for anything the email does not state --
    never omit a key, never output an empty string, never infer a value.
    Copy text verbatim from the email without normalising it.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    customer_po_text: str | None = Field(
        min_length=1,
        description=(
            "The customer purchase order reference exactly as written, "
            "e.g. PO-12345. Use null if none is given."
        ),
    )
    requested_date_text: str | None = Field(
        min_length=1,
        description=(
            "The requested delivery timing exactly as written, e.g. next Friday, "
            "by the 15th, ASAP. Do not convert it to a date. Use null if not stated."
        ),
    )
    delivery_address_text: str | None = Field(
        min_length=1,
        description=(
            "The delivery destination exactly as written, whether a full address "
            "or a site name. Use null if not stated."
        ),
    )
    buyer_name_text: str | None = Field(
        min_length=1,
        description=(
            "The name of the person placing the order, as signed or stated in the "
            "email body. Use null if no individual is identifiable."
        ),
    )
    notes: str | None = Field(
        min_length=1,
        description=(
            "Order-level delivery or handling instructions written by the "
            "customer, verbatim. Use null if none."
        ),
    )
    line_items: list[LineItem] = Field(
        description=(
            "One entry per distinct product the customer is ordering. "
            "Empty only if no products are identifiable."
        ),
    )
