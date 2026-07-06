import json

from order_desk.confidence import (
    _token_char_spans,
    field_confidences,
    overall_confidence,
)
from order_desk.extract_client import TokenLogprob
from order_desk.schemas import ExtractedOrder


def toks(pairs: list[tuple[str, float]]) -> list[TokenLogprob]:
    return [TokenLogprob(token=t, logprob=lp) for t, lp in pairs]


def test_char_spans_are_cumulative() -> None:
    spans = _token_char_spans(toks([("ab", -0.1), ("cde", -0.2), ("f", -0.3)]))
    assert spans == [(0, 2), (2, 5), (5, 6)]


def test_confidence_aligns_high_and_low_fields() -> None:
    # Build a raw JSON and a token stream that reconstructs it exactly.
    order = ExtractedOrder(
        customer_po_text="PO-1",
        requested_date_text=None,
        delivery_address_text=None,
        buyer_name_text=None,
        notes=None,
        line_items=[],
    )
    raw = json.dumps(order.model_dump(), ensure_ascii=False)
    # One token per character, confident everywhere except inside "PO-1".
    tokens = []
    po_span = raw.find('"PO-1"'), raw.find('"PO-1"') + len('"PO-1"')
    for i, ch in enumerate(raw):
        inside = po_span[0] < i < po_span[1] - 1  # the PO-1 chars, not the quotes
        tokens.append((ch, -2.0 if inside else -0.001))
    confs = field_confidences(raw, toks(tokens), order)
    assert "customer_po_text" in confs
    # span covers "PO-1" incl. quotes: 2 quote tokens at -0.001 + 4 chars at -2.0,
    # geo-mean exp(-8.002/6) ~= 0.264 -- low, and far below any confident field.
    assert confs["customer_po_text"] < 0.35


def test_confidence_covers_line_item_paths() -> None:
    order = ExtractedOrder(
        customer_po_text=None,
        requested_date_text=None,
        delivery_address_text=None,
        buyer_name_text=None,
        notes=None,
        line_items=[
            {
                "product_text": "clear tape",
                "quantity": 6,
                "unit_text": "rolls",
                "unit_price_text": None,
                "item_notes": None,
            }
        ],
    )
    raw = json.dumps(order.model_dump(), ensure_ascii=False)
    confs = field_confidences(raw, toks([(ch, -0.01) for ch in raw]), order)
    assert "line_items.0.product_text" in confs
    assert "line_items.0.quantity" in confs
    assert all(0.9 < c <= 1.0 for c in confs.values())


def test_overall_confidence_math() -> None:
    assert overall_confidence({}) == 1.0
    assert abs(overall_confidence({"a": 1.0, "b": 1.0}) - 1.0) < 1e-9
    mixed = overall_confidence({"a": 0.25, "b": 1.0})
    assert 0.4 < mixed < 0.6  # geometric mean of 0.25 and 1.0 = 0.5
