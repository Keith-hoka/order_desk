from order_desk.pipeline.graph import BLEND_ASK, run_pipeline
from order_desk.pipeline.policy import Classification, RouteDecision
from order_desk.schemas import EmailClass, ExtractedOrder

EMPTY = ExtractedOrder(
    customer_po_text=None,
    requested_date_text=None,
    delivery_address_text=None,
    buyer_name_text=None,
    notes=None,
    line_items=[],
)

ORDER = ExtractedOrder(
    customer_po_text="PO-1",
    requested_date_text=None,
    delivery_address_text=None,
    buyer_name_text=None,
    notes=None,
    line_items=[
        {
            "product_text": "tape",
            "quantity": 6,
            "unit_text": "rolls",
            "unit_price_text": None,
            "item_notes": None,
        }
    ],
)


def fake_classifier(cls: EmailClass):
    def _c(subject: str, body: str) -> Classification:
        return Classification(email_class=cls, confidence=0.9)

    return _c


def fake_extractor(order: ExtractedOrder = ORDER):
    def _e(subject: str, body: str):
        return order, {"customer_po_text": 0.95}

    return _e


def test_new_order_routes_through_extract() -> None:
    state = run_pipeline(
        "order", "send 6 rolls tape", fake_classifier(EmailClass.NEW_ORDER), fake_extractor()
    )
    assert state.route == RouteDecision.EXTRACT
    assert state.extraction is not None
    assert state.extraction.line_items[0].product_text == "tape"
    assert state.confidence == {"customer_po_text": 0.95}
    assert state.violations == []


def test_inquiry_skips_extract() -> None:
    state = run_pipeline(
        "question", "what's your lead time", fake_classifier(EmailClass.INQUIRY), fake_extractor()
    )
    assert state.route == RouteDecision.INQUIRY
    assert state.extraction is None  # extract node not reached
    assert state.violations == []


def test_cancellation_routes_to_cancel() -> None:
    state = run_pipeline(
        "cancel", "please cancel PO-9", fake_classifier(EmailClass.CANCELLATION), fake_extractor()
    )
    assert state.route == RouteDecision.CANCEL
    assert state.extraction is None
    assert state.violations == []


def test_other_is_discarded() -> None:
    state = run_pipeline(
        "newsletter", "check our deals", fake_classifier(EmailClass.OTHER), fake_extractor()
    )
    assert state.route == RouteDecision.DISCARD
    assert state.extraction is None


def test_blended_order_gets_ask() -> None:
    state = run_pipeline(
        "order plus question",
        "send 6 rolls tape. do you stock bubble wrap?",
        fake_classifier(EmailClass.NEW_ORDER),
        fake_extractor(),
    )
    assert state.route == RouteDecision.EXTRACT
    assert state.extraction is not None  # extracted normally (strategy A)
    assert BLEND_ASK in state.asks  # ...but flagged for review


def test_plain_order_no_ask() -> None:
    state = run_pipeline(
        "order",
        "please send 6 rolls of tape to the depot",
        fake_classifier(EmailClass.NEW_ORDER),
        fake_extractor(),
    )
    assert state.asks == []  # no product inquiry -> no blend ask
