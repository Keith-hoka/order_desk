from order_desk.catalog import load_catalog
from order_desk.fulfillment.resolve import (
    resolve_order,
    resolve_product,
)
from order_desk.schemas import ExtractedOrder

CAT = load_catalog()


def test_alias_exact_match() -> None:
    # "small carton" is an alias of CTN-SM-001
    m = resolve_product("small carton", CAT)
    assert m.resolved
    assert m.sku == "CTN-SM-001"
    assert m.method == "alias_exact"
    assert m.score == 100.0


def test_alias_exact_case_insensitive() -> None:
    m = resolve_product("SMALL BOX", CAT)
    assert m.resolved
    assert m.sku == "CTN-SM-001"  # "small box" is an alias


def test_name_exact_match() -> None:
    # full catalog name matches exactly (normalized)
    m = resolve_product("Small Shipping Carton 305x215x150mm", CAT)
    assert m.resolved
    assert m.sku == "CTN-SM-001"
    assert m.method == "name_exact"


def test_fuzzy_match_partial() -> None:
    # "small shipping box" is an alias, but try a near-miss phrasing
    m = resolve_product("small shipping carton", CAT)
    assert m.resolved
    assert m.sku == "CTN-SM-001"  # fuzzy or alias, either way resolves


def test_unresolved_below_threshold() -> None:
    m = resolve_product("nonexistent widget xyz", CAT)
    assert not m.resolved
    assert m.sku is None
    assert m.method == "unresolved"


def test_resolve_order_mixed() -> None:
    order = ExtractedOrder(
        customer_po_text="PO-1",
        requested_date_text=None,
        delivery_address_text=None,
        buyer_name_text=None,
        notes=None,
        line_items=[
            {
                "product_text": "small carton",
                "quantity": 50,
                "unit_text": "each",
                "unit_price_text": None,
                "item_notes": None,
            },
            {
                "product_text": "nonexistent widget xyz",
                "quantity": 3,
                "unit_text": None,
                "unit_price_text": None,
                "item_notes": None,
            },
        ],
    )
    resolved = resolve_order(order, CAT)
    assert len(resolved.lines) == 2
    assert resolved.lines[0].match.resolved
    assert resolved.lines[0].match.sku == "CTN-SM-001"
    assert not resolved.lines[1].match.resolved
    assert resolved.unresolved_count == 1
    assert not resolved.all_resolved


def test_resolve_order_all_resolved() -> None:
    order = ExtractedOrder(
        customer_po_text="PO-1",
        requested_date_text=None,
        delivery_address_text=None,
        buyer_name_text=None,
        notes=None,
        line_items=[
            {
                "product_text": "small carton",
                "quantity": 50,
                "unit_text": "each",
                "unit_price_text": None,
                "item_notes": None,
            },
        ],
    )
    resolved = resolve_order(order, CAT)
    assert resolved.all_resolved
    assert resolved.unresolved_count == 0
    assert resolved.lines[0].quantity == 50  # carries quantity through
