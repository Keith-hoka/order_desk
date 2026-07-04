"""Prompt contract for baselines and fine-tuning (step 2.1).

Locked decisions:

- One prompt set for every contestant -- gpt-4o-mini, both Qwen baselines,
  and the Phase 3 fine-tune's training data -- so comparisons measure
  models, not prompt engineering. The bundle is snapshot-pinned (editing a
  word turns CI red) and prompt_bundle_hash() stamps cache keys and reports.
- Zero-shot purity: no worked examples anywhere (few-shot is off by default
  per the Phase 2 decision record). Output structure is carried by the
  field list and, where enabled, constrained decoding.
- The extraction system prompt is machine-rendered from the pydantic
  contract: ExtractedOrder's docstring and every field description appear
  verbatim (test-enforced), so editing schemas.py trips the schema snapshot
  and the prompt snapshot together -- the 1.3 principle that field
  descriptions ARE the prompt, made mechanical.
- Classification definitions are hand-authored task definition, including
  two discriminating clauses (a quote request listing products is still an
  inquiry; an amendment refers to an existing order). Fairness argument as
  for the trap-line convention: equally visible to every contestant in the
  same words.
- The amendment capture convention is stated outright (only what the email
  itself says; removed items carry null quantity): without it the gold
  semantics for amendments would be unguessable and we would measure
  prompt-guessing, not extraction.
- Provider wire schemas (OpenAI structured outputs, xgrammar) are runner
  adapters (step 2.2), not part of this module.
"""

from __future__ import annotations

import hashlib
import inspect
from types import UnionType
from typing import Any, get_args, get_origin

from order_desk.schemas import EmailClass, ExtractedOrder, LineItem

_SENTINEL_SUBJECT = "<SUBJECT>"
_SENTINEL_BODY = "<BODY>"

_CLASS_DEFINITIONS = """\
You classify one customer email sent to Meridian Packaging Supplies, a
packaging products wholesaler.

Choose exactly one label:
- new_order: the customer is placing an order for products.
- amendment: the customer is changing an order they already placed --
  changing a quantity, adding or removing an item, or moving the delivery
  date. An amendment refers to an existing order or PO.
- cancellation: the customer asks to cancel an order they already placed.
- inquiry: the customer asks a question without placing an order -- a quote
  or pricing request, a stock or lead-time check, or a general question. A
  quote request is an inquiry even when it lists products and quantities.
- other: none of the above -- vendor marketing, misdirected mail, courier
  delivery notifications, or anything unrelated to buying packaging
  products.
"""


def classification_system_prompt() -> str:
    labels = ", ".join(member.value for member in EmailClass)
    closing = f"Respond with exactly one label: {labels}. Output only the label."
    return f"{_CLASS_DEFINITIONS}\n{closing}\n"


def _type_label(annotation: Any) -> str:
    if get_origin(annotation) is UnionType:
        args = [a for a in get_args(annotation) if a is not type(None)]
        assert len(args) == 1, annotation
        return f"{_type_label(args[0])} or null"
    if annotation is str:
        return "string"
    if annotation is int:
        return "integer"
    raise AssertionError(f"unhandled annotation {annotation!r}")


def _field_lines(model: type, *, skip: frozenset[str] = frozenset()) -> list[str]:
    lines: list[str] = []
    for name, field in model.model_fields.items():
        if name in skip:
            continue
        lines.append(f"- {name} ({_type_label(field.annotation)}): {field.description}")
    return lines


def extraction_system_prompt() -> str:
    order_fields = _field_lines(ExtractedOrder, skip=frozenset({"line_items"}))
    line_items_description = ExtractedOrder.model_fields["line_items"].description
    item_fields = _field_lines(LineItem)
    doc = inspect.cleandoc(ExtractedOrder.__doc__ or "")
    parts = [
        "You extract structured purchase-order data from one customer email"
        " sent to Meridian Packaging Supplies.",
        "",
        doc,
        "",
        "Return exactly one JSON object and nothing else: no markdown fences,"
        " no commentary before or after it.",
        "",
        "Top-level fields:",
        *order_fields,
        f"- line_items (array of line-item objects): {line_items_description}",
        "",
        "Each line-item object has:",
        *item_fields,
        "",
        "If the email amends an existing order, capture only what this email"
        " itself states: the referenced order or PO in customer_po_text; only"
        " the line items it mentions adding, changing, or removing (an item"
        " being removed carries a null quantity); and a changed delivery"
        " timing in requested_date_text.",
    ]
    return "\n".join(parts) + "\n"


def format_email(subject: str, body: str) -> str:
    """The user-message wrapper: extractor input is subject + body (step 1.5)."""
    return f"Subject: {subject}\n\n{body.rstrip()}\n"


def prompt_bundle_hash() -> str:
    """Identity of the prompt contract; stamped into cache keys and reports."""
    bundle = "\x1f".join(
        [
            classification_system_prompt(),
            extraction_system_prompt(),
            format_email(_SENTINEL_SUBJECT, _SENTINEL_BODY),
        ]
    )
    return hashlib.sha256(bundle.encode("utf-8")).hexdigest()
