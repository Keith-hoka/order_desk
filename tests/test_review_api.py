from fastapi.testclient import TestClient

from order_desk.api.app import create_app
from order_desk.api.auth import issue_token
from order_desk.api.config import Settings
from order_desk.api.review_store import InMemoryReviewStore
from order_desk.review.priority import FieldFlag, ReviewItem, ReviewStatus

SECRET = "review-api-test-secret-32-bytes-long!"


def _item(id_, priority, status=ReviewStatus.PENDING):
    return ReviewItem(
        id=id_,
        subject=f"subj-{id_}",
        body="body",
        extraction={"customer_po_text": "PO-1", "line_items": []},
        field_flags=[
            FieldFlag(
                path="customer_po_text",
                raw_confidence=0.88,
                calibrated_confidence=0.65,
                in_band=True,
            )
        ],
        asks=["blend ask"] if priority > 3 else [],
        violations=[],
        priority=priority,
        status=status,
    )


def _app(items, secret=SECRET):
    app = create_app(
        Settings(
            adapter_model="x",
            vllm_base_url="",
            vllm_api_key="EMPTY",
            jwt_secret=secret,
        )
    )
    app.state.review_store = InMemoryReviewStore(items)
    return TestClient(app)


def _auth(secret=SECRET):
    return {"Authorization": f"Bearer {issue_token(secret, 'reviewer')}"}


def test_list_exceptions_sorted_by_priority() -> None:
    client = _app([_item("low", 1.0), _item("high", 15.0), _item("mid", 5.0)])
    resp = client.get("/exceptions", headers=_auth())
    assert resp.status_code == 200
    ids = [it["id"] for it in resp.json()]
    assert ids == ["high", "mid", "low"]  # priority desc


def test_list_exceptions_shape() -> None:
    client = _app([_item("a", 5.0)])
    item = client.get("/exceptions", headers=_auth()).json()[0]
    assert item["priority"] == 5.0
    assert item["field_flags"][0]["in_band"] is True
    assert item["field_flags"][0]["raw_confidence"] == 0.88
    assert item["status"] == "pending"
    assert item["asks"] == ["blend ask"]


def test_get_single_exception() -> None:
    client = _app([_item("x", 5.0)])
    resp = client.get("/exceptions/x", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["id"] == "x"


def test_get_missing_exception_404() -> None:
    client = _app([_item("x", 5.0)])
    assert client.get("/exceptions/nope", headers=_auth()).status_code == 404


def test_submit_review_approve() -> None:
    client = _app([_item("x", 5.0)])
    resp = client.post(
        "/exceptions/x/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    # persisted: subsequent GET reflects it
    assert client.get("/exceptions/x", headers=_auth()).json()["status"] == "approved"


def test_submit_review_edit_records_edits() -> None:
    client = _app([_item("x", 5.0)])
    resp = client.post(
        "/exceptions/x/review",
        headers=_auth(),
        json={"action": "edited", "edits": {"delivery_address_text": "Eagle Farm"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "edited"
    assert data["edits"]["delivery_address_text"] == "Eagle Farm"


def test_submit_review_reject() -> None:
    client = _app([_item("x", 5.0)])
    resp = client.post(
        "/exceptions/x/review", headers=_auth(), json={"action": "rejected", "edits": {}}
    )
    assert resp.json()["status"] == "rejected"


def test_review_requires_auth() -> None:
    client = _app([_item("x", 5.0)])
    assert client.get("/exceptions").status_code == 401
    assert client.post("/exceptions/x/review", json={"action": "approved"}).status_code == 401


def test_review_503_without_store() -> None:
    app = create_app(
        Settings(
            adapter_model="x",
            vllm_base_url="",
            vllm_api_key="EMPTY",
            jwt_secret=SECRET,
        )
    )
    # review_store left as None (no queue path)
    client = TestClient(app)
    assert client.get("/exceptions", headers=_auth()).status_code == 503


# --- Phase 8: approve triggers fulfillment ---


def _order_item(id_, product_text, qty):
    from order_desk.review.priority import ReviewItem, ReviewStatus

    return ReviewItem(
        id=id_,
        subject=f"order-{id_}",
        body="body",
        extraction={
            "customer_po_text": "PO-9",
            "requested_date_text": None,
            "delivery_address_text": "Botany",
            "buyer_name_text": "Dana",
            "notes": None,
            "line_items": [
                {
                    "product_text": product_text,
                    "quantity": qty,
                    "unit_text": "each",
                    "unit_price_text": None,
                    "item_notes": None,
                }
            ],
        },
        field_flags=[],
        asks=[],
        violations=[],
        priority=1.0,
        status=ReviewStatus.PENDING,
    )


def _app_with_fulfillment(items):
    from order_desk.fulfillment.notify import MockNotifier

    app = create_app(
        Settings(
            adapter_model="x",
            vllm_base_url="",
            vllm_api_key="EMPTY",
            jwt_secret=SECRET,
        )
    )
    app.state.review_store = InMemoryReviewStore(items)

    class FakeSink:
        def __init__(self):
            self.submitted = []

        def submit(self, order):
            from order_desk.fulfillment.erp import OrderReceipt

            self.submitted.append(order)
            return OrderReceipt(
                order_id="ORD-APITEST",
                status="accepted",
                submitted_at="2026-01-01T00:00:00Z",
                total_cents=order.total_cents,
            )

    app.state.order_sink = FakeSink()
    app.state.notifier = MockNotifier()
    return TestClient(app), app


def test_approve_clean_order_submits_to_erp() -> None:
    # small carton moq 25; qty 50 resolves + validates
    client, app = _app_with_fulfillment([_order_item("EXC-1", "small carton", 50)])
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["fulfillment"]["submitted"] is True
    assert data["fulfillment"]["order_id"] == "ORD-APITEST"
    assert data["fulfillment"]["reason"] == "submitted"
    # sink actually received it
    assert len(app.state.order_sink.submitted) == 1
    # notification sent
    assert len(app.state.notifier.sent) == 1


def test_approve_unresolved_holds() -> None:
    client, app = _app_with_fulfillment([_order_item("EXC-2", "mystery widget xyz", 50)])
    resp = client.post(
        "/exceptions/EXC-2/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    data = resp.json()
    assert data["status"] == "approved"  # approval still succeeds
    assert data["fulfillment"]["submitted"] is False
    assert data["fulfillment"]["reason"] == "held_for_mapping"
    assert "mystery widget xyz" in data["fulfillment"]["unresolved"]
    assert len(app.state.order_sink.submitted) == 0  # nothing submitted


def test_reject_does_not_fulfill() -> None:
    client, app = _app_with_fulfillment([_order_item("EXC-3", "small carton", 50)])
    resp = client.post(
        "/exceptions/EXC-3/review", headers=_auth(), json={"action": "rejected", "edits": {}}
    )
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["fulfillment"] is None  # only approve fulfills
    assert len(app.state.order_sink.submitted) == 0
