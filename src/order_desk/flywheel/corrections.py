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
paths into the nested extraction dict.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from order_desk.review.priority import ReviewItem, ReviewStatus


@dataclass
class Correction:
    item_id: str
    subject: str
    body: str
    original_extraction: dict
    corrected_extraction: dict
    correction_type: str  # "edited" | "rejected"


def apply_edits(extraction: dict, edits: dict[str, str]) -> dict:
    """Apply flat field-path edits to a copy of the extraction.

    Paths are dot-separated; a numeric segment indexes a list, e.g.
    "line_items.0.product_text". Values are strings from the review UI; numeric
    fields (quantity) are coerced to int when the existing value is an int.
    """
    result = copy.deepcopy(extraction)
    for path, value in edits.items():
        segments = path.split(".")
        target = result
        for seg in segments[:-1]:
            key: int | str = int(seg) if seg.isdigit() else seg
            target = target[key]
        last = segments[-1]
        last_key: int | str = int(last) if last.isdigit() else last
        # coerce to int if the field being replaced currently holds an int
        existing = (
            target[last_key] if not isinstance(last_key, int) or last_key < len(target) else None
        )
        if isinstance(existing, int) and not isinstance(existing, bool):
            target[last_key] = int(value)
        else:
            target[last_key] = value
    return result


def correction_from_item(item: ReviewItem) -> Correction | None:
    """Build a Correction from an edited or rejected item; None otherwise."""
    if item.extraction is None:
        return None
    if item.status == ReviewStatus.EDITED:
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
