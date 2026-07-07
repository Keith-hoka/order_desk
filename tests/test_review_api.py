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
