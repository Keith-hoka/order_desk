from order_desk.flywheel.corrections import (
    LINE_DELETED,
    adapter_training_corrections,
    apply_edits,
    correction_from_item,
    extract_corrections,
)
from order_desk.review.priority import ReviewItem, ReviewStatus

BASE_EXTRACTION = {
    "customer_po_text": "PO-1",
    "requested_date_text": None,
    "delivery_address_text": "Botny",
    "buyer_name_text": "Dana",
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
            "product_text": "bubble wrap",
            "quantity": 1,
            "unit_text": "roll",
            "unit_price_text": None,
            "item_notes": None,
        },
    ],
}


def _item(status, edits=None, extraction=None):
    return ReviewItem(
        id="EXC-1",
        subject="order",
        body="send 50 small cartons",
        extraction=extraction if extraction is not None else dict(BASE_EXTRACTION),
        field_flags=[],
        asks=[],
        violations=[],
        priority=1.0,
        status=status,
        edits=edits or {},
    )


def test_apply_edits_top_level_field() -> None:
    # fix a misspelled address
    edited = apply_edits(BASE_EXTRACTION, {"delivery_address_text": "Botany"})
    assert edited["delivery_address_text"] == "Botany"
    assert BASE_EXTRACTION["delivery_address_text"] == "Botny"  # original untouched


def test_apply_edits_line_item_field() -> None:
    edited = apply_edits(BASE_EXTRACTION, {"line_items.0.product_text": "small shipping carton"})
    assert edited["line_items"][0]["product_text"] == "small shipping carton"


def test_apply_edits_deletes_line_item() -> None:
    # the model split one product into two lines; the reviewer removes the extra
    edited = apply_edits(BASE_EXTRACTION, {"line_items.1": LINE_DELETED})
    assert len(edited["line_items"]) == 1
    assert edited["line_items"][0]["product_text"] == "small carton"
    assert len(BASE_EXTRACTION["line_items"]) == 2  # original untouched


def test_apply_edits_field_edit_and_deletion_combine() -> None:
    # field edits address original indices; deletions apply afterwards
    edited = apply_edits(
        BASE_EXTRACTION,
        {"line_items.0.quantity": "75", "line_items.1": LINE_DELETED},
    )
    assert len(edited["line_items"]) == 1
    assert edited["line_items"][0]["quantity"] == 75


def test_apply_edits_multiple_deletions() -> None:
    edited = apply_edits(
        BASE_EXTRACTION, {"line_items.0": LINE_DELETED, "line_items.1": LINE_DELETED}
    )
    assert edited["line_items"] == []


def test_apply_edits_builds_extraction_from_none() -> None:
    """A routed-away item has no extraction; the reviewer creates one by hand.

    Edits over None start from an empty skeleton, and a line index one past the
    end grows the list -- so "line_items.0.product_text" on an empty order
    creates line 0.
    """
    edited = apply_edits(
        None,
        {
            "customer_po_text": "PO-7",
            "delivery_address_text": "Botany",
            "line_items.0.product_text": "small carton",
            "line_items.0.quantity": "50",
        },
    )
    assert edited["customer_po_text"] == "PO-7"
    assert edited["buyer_name_text"] is None  # untouched skeleton field
    assert edited["line_items"][0]["product_text"] == "small carton"
    assert edited["line_items"][0]["quantity"] == 50


def test_apply_edits_appends_new_lines_to_existing_extraction() -> None:
    """Orders rarely have one line; edits past the end append new lines."""
    edited = apply_edits(
        BASE_EXTRACTION,
        {
            "line_items.2.product_text": "packing tape",
            "line_items.2.quantity": "36",
            "line_items.3.product_text": "labels",
            "line_items.3.quantity": "4",
        },
    )
    assert len(edited["line_items"]) == 4
    assert edited["line_items"][2]["product_text"] == "packing tape"
    assert edited["line_items"][3]["quantity"] == 4


def test_apply_edits_deleting_never_created_line_is_noop() -> None:
    """Adding a row in the UI then removing it before filling must net to zero."""
    edited = apply_edits(BASE_EXTRACTION, {"line_items.2": LINE_DELETED})
    assert len(edited["line_items"]) == 2


def test_apply_edits_coerces_int_quantity() -> None:
    # quantity currently int -> edit value coerced to int
    edited = apply_edits(BASE_EXTRACTION, {"line_items.0.quantity": "75"})
    assert edited["line_items"][0]["quantity"] == 75
    assert isinstance(edited["line_items"][0]["quantity"], int)


def test_approved_item_with_edits_stays_a_correction() -> None:
    """Approving corrected fields is still a correction signal.

    The reviewer's decision (approved) and the correction (edits) are separate
    facts; keying the flywheel on status alone would drop every correction the
    moment the reviewer confirms it.
    """
    item = _item(ReviewStatus.APPROVED, edits={"delivery_address_text": "Botany"})
    c = correction_from_item(item)
    assert c is not None
    assert c.correction_type == "edited"
    assert c.corrected_extraction["delivery_address_text"] == "Botany"


def test_edited_item_becomes_correction() -> None:
    item = _item(ReviewStatus.EDITED, edits={"delivery_address_text": "Botany"})
    c = correction_from_item(item)
    assert c is not None
    assert c.correction_type == "edited"
    assert c.corrected_extraction["delivery_address_text"] == "Botany"
    assert c.original_extraction["delivery_address_text"] == "Botny"


def test_rejected_item_captured_as_rejected() -> None:
    item = _item(ReviewStatus.REJECTED)
    c = correction_from_item(item)
    assert c is not None
    assert c.correction_type == "rejected"


def test_pending_and_approved_yield_no_correction() -> None:
    assert correction_from_item(_item(ReviewStatus.PENDING)) is None
    assert correction_from_item(_item(ReviewStatus.APPROVED)) is None


def test_extract_corrections_filters() -> None:
    items = [
        _item(ReviewStatus.EDITED, edits={"delivery_address_text": "Botany"}),
        _item(ReviewStatus.APPROVED),
        _item(ReviewStatus.REJECTED),
        _item(ReviewStatus.PENDING),
    ]
    corrections = extract_corrections(items)
    assert len(corrections) == 2  # edited + rejected only


def test_adapter_training_corrections_excludes_rejected() -> None:
    items = [
        _item(ReviewStatus.EDITED, edits={"delivery_address_text": "Botany"}),
        _item(ReviewStatus.REJECTED),
    ]
    training = adapter_training_corrections(extract_corrections(items))
    assert len(training) == 1  # only edited is an adapter target
    assert training[0].correction_type == "edited"
