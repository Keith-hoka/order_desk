import json
from pathlib import Path

from order_desk.catalog import load_catalog
from order_desk.fulfillment.erp import (
    LocalOrderSink,
    build_erp_order,
)
from order_desk.fulfillment.resolve import resolve_order
from order_desk.schemas import ExtractedOrder

CAT = load_catalog()


def _order(items):
    return ExtractedOrder(
        customer_po_text="PO-9",
        requested_date_text=None,
        delivery_address_text="Botany",
        buyer_name_text="Dana",
        notes=None,
        line_items=items,
    )


def _item(product_text, qty):
    return {
        "product_text": product_text,
        "quantity": qty,
        "unit_text": "each",
        "unit_price_text": None,
        "item_notes": None,
    }


def test_build_erp_order_all_resolved() -> None:
    # small carton moq is 25; use 50
    ex = _order([_item("small carton", 50)])
    result = build_erp_order(resolve_order(ex, CAT), ex, CAT)
    assert result.ok
    assert result.order is not None
    assert len(result.order.lines) == 1
    line = result.order.lines[0]
    assert line.sku == "CTN-SM-001"
    assert line.quantity == 50
    assert line.unit_price_cents == 95
    assert line.line_total_cents == 50 * 95
    assert result.order.customer_po == "PO-9"
    assert result.order.total_cents == 4750


def test_unresolved_blocks_whole_order() -> None:
    # decision B: one unresolved product blocks the entire order
    ex = _order([_item("small carton", 50), _item("nonexistent widget", 3)])
    result = build_erp_order(resolve_order(ex, CAT), ex, CAT)
    assert not result.ok
    assert result.order is None  # blocked
    assert "nonexistent widget" in result.unresolved


def test_below_moq_blocks_order() -> None:
    # small carton moq is 25; ordering 5 violates it
    ex = _order([_item("small carton", 5)])
    result = build_erp_order(resolve_order(ex, CAT), ex, CAT)
    assert not result.ok
    assert result.order is None
    assert result.quantity_issues[0].kind == "below_moq"
    assert result.quantity_issues[0].sku == "CTN-SM-001"


def test_missing_quantity_blocks_order() -> None:
    ex = _order([_item("small carton", None)])
    result = build_erp_order(resolve_order(ex, CAT), ex, CAT)
    assert not result.ok
    assert result.quantity_issues[0].kind == "missing"


def test_local_sink_writes_and_returns_receipt(tmp_path: Path) -> None:
    sink = LocalOrderSink(tmp_path / "erp_orders.json")
    ex = _order([_item("small carton", 50)])
    built = build_erp_order(resolve_order(ex, CAT), ex, CAT).order
    receipt = sink.submit(built)
    assert receipt.order_id.startswith("ORD-")
    assert receipt.status == "accepted"
    assert receipt.total_cents == 4750
    # persisted
    records = json.loads((tmp_path / "erp_orders.json").read_text())
    assert len(records) == 1
    assert records[0]["receipt"]["order_id"] == receipt.order_id
    assert records[0]["order"]["lines"][0]["sku"] == "CTN-SM-001"


def test_local_sink_appends(tmp_path: Path) -> None:
    sink = LocalOrderSink(tmp_path / "erp.json")
    ex = _order([_item("small carton", 50)])
    built = build_erp_order(resolve_order(ex, CAT), ex, CAT).order
    r1 = sink.submit(built)
    r2 = sink.submit(built)
    assert r1.order_id != r2.order_id  # unique ids
    records = json.loads((tmp_path / "erp.json").read_text())
    assert len(records) == 2
