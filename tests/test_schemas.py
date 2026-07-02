import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from order_desk.schemas import EmailClass, ExtractedOrder

SNAPSHOT = Path(__file__).parent / "snapshots" / "extracted_order.schema.json"

PAYLOAD: dict[str, Any] = {
    "customer_po_text": "PO-48213",
    "requested_date_text": "by next Friday",
    "delivery_address_text": "Eastern Creek DC",
    "buyer_name_text": "Dana",
    "notes": "tailgate required",
    "line_items": [
        {"product_text": "shrink wrap", "quantity": 12, "unit_text": "rolls", "item_notes": None},
        {
            "product_text": "clear packing tape",
            "quantity": 72,
            "unit_text": None,
            "item_notes": "brown is fine if clear is out",
        },
    ],
}


def valid_payload() -> dict[str, Any]:
    return json.loads(json.dumps(PAYLOAD))


def test_round_trips_full_example() -> None:
    order = ExtractedOrder.model_validate(valid_payload())
    assert order.model_dump() == PAYLOAD
    assert ExtractedOrder.model_validate_json(json.dumps(PAYLOAD)) == order


def test_every_key_is_required() -> None:
    for key in PAYLOAD:
        broken = valid_payload()
        broken.pop(key)
        with pytest.raises(ValidationError):
            ExtractedOrder.model_validate(broken)


def test_explicit_nulls_and_empty_line_items_are_valid() -> None:
    empty = {
        "customer_po_text": None,
        "requested_date_text": None,
        "delivery_address_text": None,
        "buyer_name_text": None,
        "notes": None,
        "line_items": [],
    }
    order = ExtractedOrder.model_validate(empty)
    assert order.line_items == []


def test_unknown_keys_are_rejected() -> None:
    broken = valid_payload()
    broken["sku"] = "CTN-SM-001"
    with pytest.raises(ValidationError):
        ExtractedOrder.model_validate(broken)


def test_empty_strings_are_rejected_where_null_is_meant() -> None:
    broken = valid_payload()
    broken["notes"] = ""
    with pytest.raises(ValidationError):
        ExtractedOrder.model_validate(broken)
    broken = valid_payload()
    broken["line_items"][0]["product_text"] = ""
    with pytest.raises(ValidationError):
        ExtractedOrder.model_validate(broken)


def test_nonpositive_quantity_is_rejected() -> None:
    broken = valid_payload()
    broken["line_items"][0]["quantity"] = 0
    with pytest.raises(ValidationError):
        ExtractedOrder.model_validate(broken)


def test_strict_mode_rejects_numeric_strings() -> None:
    broken = valid_payload()
    broken["line_items"][0]["quantity"] = "12"
    with pytest.raises(ValidationError):
        ExtractedOrder.model_validate(broken)


def test_schema_declares_closed_objects_and_full_required() -> None:
    schema = ExtractedOrder.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["LineItem"]["additionalProperties"] is False
    assert set(schema["required"]) == set(PAYLOAD)


def test_json_schema_matches_committed_snapshot() -> None:
    live = ExtractedOrder.model_json_schema()
    committed = json.loads(SNAPSHOT.read_text())
    assert live == committed, (
        "extraction contract drifted; if intentional, run "
        "`uv run python scripts/write_schema_snapshot.py` and commit the result"
    )


def test_email_class_labels_match_spec() -> None:
    assert {c.value for c in EmailClass} == {
        "new_order",
        "amendment",
        "cancellation",
        "inquiry",
        "other",
    }
