from order_desk.fulfillment.notify import (
    MockNotifier,
    Notification,
    NotifyEvent,
    build_notifier,
    needs_mapping_message,
    order_submitted_message,
)


def test_order_submitted_message() -> None:
    msg = order_submitted_message(po="PO-73218", order_id="ORD-ABC123", n_lines=2, total_cents=4750)
    assert "PO-73218" in msg
    assert "ORD-ABC123" in msg
    assert "2 lines" in msg
    assert "$47.50" in msg


def test_order_submitted_singular_line() -> None:
    msg = order_submitted_message(po="PO-1", order_id="ORD-X", n_lines=1, total_cents=95)
    assert "1 line" in msg
    assert "1 lines" not in msg  # singular


def test_order_submitted_no_po() -> None:
    msg = order_submitted_message(po=None, order_id="ORD-X", n_lines=1, total_cents=100)
    assert "(no PO)" in msg


def test_needs_mapping_message_unresolved() -> None:
    msg = needs_mapping_message(po="PO-9", unresolved=["widget xyz"], issues=[])
    assert "PO-9" in msg
    assert "widget xyz" in msg
    assert "not matched" in msg


def test_needs_mapping_message_issues() -> None:
    msg = needs_mapping_message(po="PO-9", unresolved=[], issues=["CTN-SM-001 below moq"])
    assert "quantity issue" in msg
    assert "CTN-SM-001 below moq" in msg


def test_mock_notifier_records() -> None:
    n = MockNotifier()
    n.send(Notification(event=NotifyEvent.ORDER_SUBMITTED, text="hello"))
    n.send(Notification(event=NotifyEvent.NEEDS_MAPPING, text="world"))
    assert len(n.sent) == 2
    assert n.sent[0].event == NotifyEvent.ORDER_SUBMITTED
    assert n.sent[1].text == "world"


def test_build_notifier_mock_when_no_webhook() -> None:
    n = build_notifier(None)
    assert isinstance(n, MockNotifier)


def test_build_notifier_real_when_webhook() -> None:
    from order_desk.fulfillment.notify import SlackWebhookNotifier

    n = build_notifier("https://hooks.slack.com/services/XXX")
    assert isinstance(n, SlackWebhookNotifier)
