"""Extract retraining signal from reviewer corrections (Phase 9).

A reviewer who edits an extraction is telling us the correct answer for a case
the model got wrong -- exactly the targeted signal a flywheel needs. This module
turns review-store decisions into Corrections: for an edited item, it applies
the field-path edits to the original extraction to reconstruct the corrected
extraction (the new gold); a rejected item is captured but marked, since a
rejection often means "not an order at all" (a classification signal) rather
than "extract it differently" (the adapter signal we retrain on).

Edits are flat field paths -> values, mirroring the review UI:
"delivery_address_text" or "line_items.0.product_text". apply_edits walks those
paths into the nested extraction dict. A whole-line path with the LINE_DELETED
value ("line_items.1": LINE_DELETED) removes that line -- the reviewer's signal
that the model invented a line item that is not in the email.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from order_desk.review.priority import ReviewItem, ReviewStatus

LINE_DELETED = "__deleted__"


def empty_extraction() -> dict:
    """The starting point for a reviewer building an order from scratch."""
    return {
        "customer_po_text": None,
        "requested_date_text": None,
        "delivery_address_text": None,
        "buyer_name_text": None,
        "notes": None,
        "line_items": [],
    }


def _empty_line_item() -> dict:
    return {
        "product_text": None,
        "quantity": None,
        "unit_text": None,
        "unit_price_text": None,
        "item_notes": None,
    }


@dataclass
class Correction:
    item_id: str
    subject: str
    body: str
    original_extraction: dict
    corrected_extraction: dict
    correction_type: str  # "edited" | "rejected"


def apply_edits(extraction: dict | None, edits: dict[str, str]) -> dict:
    """Apply flat field-path edits to a copy of the extraction.

    Paths are dot-separated; a numeric segment indexes a list, e.g.
    "line_items.0.product_text". Values are strings from the review UI; numeric
    fields (quantity) are coerced to int when the existing value is an int.
    Field edits address original indices; LINE_DELETED deletions apply last,
    highest index first, so the two never shift each other.

    A None extraction (routed-away item) starts from an empty skeleton, and a
    line index one past the end appends an empty line -- together these let a
    reviewer build an order the router missed entirely.
    """
    result = copy.deepcopy(extraction) if extraction is not None else empty_extraction()
    deletions: list[int] = []
    for path, value in edits.items():
        segments = path.split(".")
        if value == LINE_DELETED:
            deletions.append(int(segments[1]))
            continue
        target = result
        for seg in segments[:-1]:
            key: int | str = int(seg) if seg.isdigit() else seg
            if isinstance(key, int) and isinstance(target, list) and key == len(target):
                target.append(_empty_line_item())
            target = target[key]
        last = segments[-1]
        last_key: int | str = int(last) if last.isdigit() else last
        # quantity is the schema's one integer field; coerce by field name --
        # keying off the existing value's type fails whenever it is None
        if last_key == "quantity" and value.strip().lstrip("-").isdigit():
            target[last_key] = int(value)
        else:
            target[last_key] = value
    for idx in sorted(deletions, reverse=True):
        # a deletion of a line no edit ever created (added in the UI, removed
        # again before filling) nets to nothing
        if idx < len(result["line_items"]):
            del result["line_items"][idx]
    return result


def correction_from_item(item: ReviewItem) -> Correction | None:
    """Build a Correction from an edited or rejected item; None otherwise."""
    if item.extraction is None:
        return None
    # edits, not status, mark a correction: an approved item whose fields were
    # corrected first is still the reviewer telling us the right answer
    if item.status in (ReviewStatus.EDITED, ReviewStatus.APPROVED) and item.edits:
        corrected = apply_edits(item.extraction, item.edits)
        return Correction(
            item_id=item.id,
            subject=item.subject,
            body=item.body,
            original_extraction=item.extraction,
            corrected_extraction=corrected,
            correction_type="edited",
        )
    if item.status == ReviewStatus.REJECTED:
        # rejection: capture, but the corrected extraction is unknown here
        # (often a classification signal, not an adapter re-extraction target)
        return Correction(
            item_id=item.id,
            subject=item.subject,
            body=item.body,
            original_extraction=item.extraction,
            corrected_extraction=item.extraction,
            correction_type="rejected",
        )
    return None


def extract_corrections(items: list[ReviewItem]) -> list[Correction]:
    """Extract all corrections from a list of reviewed items."""
    corrections = []
    for item in items:
        c = correction_from_item(item)
        if c is not None:
            corrections.append(c)
    return corrections


def adapter_training_corrections(corrections: list[Correction]) -> list[Correction]:
    """Only edited corrections are direct adapter re-extraction targets.

    Rejections are excluded: a rejected extraction does not tell the adapter the
    right line items to emit (it more often means the email was misclassified),
    so feeding it as an extraction target would be wrong signal.
    """
    return [c for c in corrections if c.correction_type == "edited"]
