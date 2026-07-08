from order_desk.fulfillment.fulfill import fulfill_order
from order_desk.fulfillment.notify import MockNotifier, NotifyEvent


class FakeSink:
    def __init__(self):
        self.submitted = []

    def submit(self, order):
        from order_desk.fulfillment.erp import OrderReceipt

        receipt = OrderReceipt(
            order_id="ORD-TEST01",
            status="accepted",
            submitted_at="2026-01-01T00:00:00Z",
            total_cents=order.total_cents,
        )
        self.submitted.append(order)
        return receipt


def _extraction(items, po="PO-9"):
    return {
        "customer_po_text": po,
        "requested_date_text": None,
        "delivery_address_text": "Botany",
        "buyer_name_text": "Dana",
        "notes": None,
        "line_items": items,
    }


def _item(product_text, qty):
    return {
        "product_text": product_text,
        "quantity": qty,
        "unit_text": "each",
        "unit_price_text": None,
        "item_notes": None,
    }


def test_fulfill_submits_clean_order() -> None:
    sink, notifier = FakeSink(), MockNotifier()
    # small carton moq 25; use 50
    result = fulfill_order(_extraction([_item("small carton", 50)]), sink, notifier)
    assert result.submitted
    assert result.order_id == "ORD-TEST01"
    assert result.reason == "submitted"
    assert len(sink.submitted) == 1
    assert len(notifier.sent) == 1
    assert notifier.sent[0].event == NotifyEvent.ORDER_SUBMITTED
    assert "PO-9" in notifier.sent[0].text


def test_fulfill_holds_unresolved() -> None:
    sink, notifier = FakeSink(), MockNotifier()
    result = fulfill_order(
        _extraction([_item("small carton", 50), _item("mystery widget", 3)]), sink, notifier
    )
    assert not result.submitted
    assert result.reason == "held_for_mapping"
    assert "mystery widget" in result.unresolved
    assert len(sink.submitted) == 0  # nothing submitted (decision B)
    assert notifier.sent[0].event == NotifyEvent.NEEDS_MAPPING


def test_fulfill_holds_on_moq_violation() -> None:
    sink, notifier = FakeSink(), MockNotifier()
    # small carton moq 25; ordering 5 violates
    result = fulfill_order(_extraction([_item("small carton", 5)]), sink, notifier)
    assert not result.submitted
    assert len(sink.submitted) == 0
    assert notifier.sent[0].event == NotifyEvent.NEEDS_MAPPING
    assert "below_moq" in notifier.sent[0].text
