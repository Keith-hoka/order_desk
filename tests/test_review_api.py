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
        extraction={
            "customer_po_text": "PO-1",
            "delivery_address_text": "Botany",
            "buyer_name_text": "Dana",
            "requested_date_text": "2026-08-01",
            "line_items": [
                {
                    "product_text": "small carton",
                    "quantity": 50,
                    "unit_text": "each",
                    "unit_price_text": None,
                    "item_notes": None,
                }
            ],
        },
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


def test_approve_after_edit_keeps_corrections() -> None:
    """Approving an already-edited item confirms the corrected version.

    The status becomes approved -- the reviewer's last decision -- while the
    edits stay: wiping them would revert the UI to the model's output, drop the
    flywheel's correction signal, and send the uncorrected order to the ERP.
    """
    client = _app([_item("x", 5.0)])
    client.post(
        "/exceptions/x/review",
        headers=_auth(),
        json={"action": "edited", "edits": {"delivery_address_text": "Eagle Farm"}},
    )
    resp = client.post(
        "/exceptions/x/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    data = resp.json()
    assert data["status"] == "approved"
    assert data["edits"]["delivery_address_text"] == "Eagle Farm"


def test_reject_after_edit_shows_rejected() -> None:
    client = _app([_item("x", 5.0)])
    client.post(
        "/exceptions/x/review",
        headers=_auth(),
        json={"action": "edited", "edits": {"delivery_address_text": "Eagle Farm"}},
    )
    resp = client.post(
        "/exceptions/x/review", headers=_auth(), json={"action": "rejected", "edits": {}}
    )
    assert resp.json()["status"] == "rejected"


def test_json_store_approve_after_edit_keeps_corrections(tmp_path) -> None:
    import json

    from order_desk.api.review_store import JsonReviewStore, item_to_dict

    path = tmp_path / "queue.json"
    path.write_text(json.dumps([item_to_dict(_item("x", 5.0))]))
    store = JsonReviewStore(path)
    store.submit_review("x", ReviewStatus.EDITED, {"delivery_address_text": "Eagle Farm"})
    store.submit_review("x", ReviewStatus.APPROVED, {})
    reloaded = JsonReviewStore(path).get_item("x")
    assert reloaded.status == ReviewStatus.APPROVED
    assert reloaded.edits == {"delivery_address_text": "Eagle Farm"}


def test_json_store_persists_fulfillment(tmp_path) -> None:
    import json

    from order_desk.api.review_store import JsonReviewStore, item_to_dict

    path = tmp_path / "queue.json"
    path.write_text(json.dumps([item_to_dict(_item("x", 5.0))]))
    store = JsonReviewStore(path)
    receipt = {
        "submitted": True,
        "order_id": "ORD-1",
        "reason": "submitted",
        "unresolved": [],
        "amends": None,
        "for_edits": {},
    }
    store.record_fulfillment("x", receipt)
    assert JsonReviewStore(path).get_item("x").fulfillment == receipt


def test_submit_review_reject() -> None:
    client = _app([_item("x", 5.0)])
    resp = client.post(
        "/exceptions/x/review", headers=_auth(), json={"action": "rejected", "edits": {}}
    )
    assert resp.json()["status"] == "rejected"


class _FakeLiveExtractor:
    def extract(self, subject, body, item_id):
        from order_desk.review.priority import ReviewItem

        return ReviewItem(
            id=item_id,
            subject=subject,
            body=body,
            extraction={
                "customer_po_text": "PO-LIVE",
                "delivery_address_text": None,
                "buyer_name_text": None,
                "requested_date_text": None,
                "notes": None,
                "line_items": [],
            },
            field_flags=[],
            asks=[],
            violations=[],
            priority=1.0,
        )


def test_live_extract_appends_to_queue() -> None:
    client = _app([_item("x", 5.0)])
    client.app.state.live_extractor = _FakeLiveExtractor()
    resp = client.post(
        "/exceptions/extract",
        headers=_auth(),
        json={"subject": "new order", "body": "20 rolls of tape"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["subject"] == "new order"
    assert data["status"] == "pending"
    # it is now in the reviewer's queue
    ids = [it["id"] for it in client.get("/exceptions", headers=_auth()).json()]
    assert data["id"] in ids


def test_live_extract_scoped_to_caller_org() -> None:
    from order_desk.api.auth import issue_token

    client = _app([])
    client.app.state.live_extractor = _FakeLiveExtractor()
    org_a = {"Authorization": f"Bearer {issue_token(SECRET, 'a', org_id='org-a')}"}
    org_b = {"Authorization": f"Bearer {issue_token(SECRET, 'b', org_id='org-b')}"}
    created = client.post(
        "/exceptions/extract", headers=org_a, json={"subject": "s", "body": "b"}
    ).json()
    assert created["id"] in [it["id"] for it in client.get("/exceptions", headers=org_a).json()]
    assert created["id"] not in [it["id"] for it in client.get("/exceptions", headers=org_b).json()]


class _FakeInboxImap:
    """Fake imaplib.IMAP4_SSL serving two unseen order emails."""

    def __init__(self, host):
        self.host = host

    def login(self, user, password):
        return "OK", []

    def select(self, mailbox):
        return "OK", []

    def search(self, charset, criteria):
        return "OK", [b"1 2"]

    def fetch(self, num, parts):
        raw = (
            f"Subject: order {num.decode()}\r\nFrom: c@x.com\r\n\r\n"
            f"please send {num.decode()} boxes"
        ).encode()
        return "OK", [(b"1 (RFC822 {10}", raw), b")"]

    def logout(self):
        return "BYE", []


def _mailbox_app(items, live_extractor=None):
    app = create_app(
        Settings(
            adapter_model="x",
            vllm_base_url="",
            vllm_api_key="EMPTY",
            jwt_secret=SECRET,
            imap_host="imap.example.com",
            imap_username="orders@example.com",
            imap_password="pw",
        )
    )
    app.state.review_store = InMemoryReviewStore(items)
    app.state.live_extractor = live_extractor
    return TestClient(app)


class _FakeRawExtractor:
    def extract_raw(self, raw, item_id):
        from order_desk.review.priority import ReviewItem

        subject = raw.splitlines()[0].removeprefix("Subject: ")
        return ReviewItem(
            id=item_id,
            subject=subject,
            body=raw,
            extraction=None,
            field_flags=[],
            asks=[],
            violations=[],
            priority=1.0,
        )


def test_extract_inbox_pulls_recent_unseen(monkeypatch) -> None:
    import imaplib

    monkeypatch.setattr(imaplib, "IMAP4_SSL", _FakeInboxImap)
    client = _mailbox_app([], live_extractor=_FakeRawExtractor())
    resp = client.post(
        "/exceptions/extract-inbox", headers=_auth(), json={"address": "orders@example.com"}
    )
    assert resp.status_code == 200
    created = resp.json()
    assert len(created) == 2
    assert {c["subject"] for c in created} == {"order 1", "order 2"}
    ids = [it["id"] for it in client.get("/exceptions", headers=_auth()).json()]
    assert all(c["id"] in ids for c in created)


class _CapturingImap(_FakeInboxImap):
    """Records what credentials the connection was opened with."""

    seen: list[tuple] = []

    def __init__(self, host):
        super().__init__(host)
        _CapturingImap.seen.append(("host", host))

    def login(self, user, password):
        _CapturingImap.seen.append(("login", user, password))
        return "OK", []


def test_extract_inbox_uses_reviewer_credentials(monkeypatch) -> None:
    """A reviewer without .env access supplies their own mailbox per request.

    The credentials are request-scoped: used for the connection, never stored.
    """
    import imaplib

    monkeypatch.setattr(imaplib, "IMAP4_SSL", _CapturingImap)
    _CapturingImap.seen.clear()
    client = _mailbox_app([], live_extractor=_FakeRawExtractor())
    resp = client.post(
        "/exceptions/extract-inbox",
        headers=_auth(),
        json={
            "address": "reviewer@own-mail.com",
            "host": "imap.own-mail.com",
            "password": "own-app-password",
        },
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    assert ("host", "imap.own-mail.com") in _CapturingImap.seen
    assert ("login", "reviewer@own-mail.com", "own-app-password") in _CapturingImap.seen


def test_extract_inbox_password_without_host_is_rejected() -> None:
    client = _mailbox_app([], live_extractor=_FakeRawExtractor())
    resp = client.post(
        "/exceptions/extract-inbox",
        headers=_auth(),
        json={"address": "reviewer@own-mail.com", "password": "pw"},
    )
    assert resp.status_code == 400


def test_delete_live_item() -> None:
    client = _app([_item("EXC-AB12CD", 1.0), _item("EXC-0003", 1.0)])
    resp = client.delete("/exceptions/EXC-AB12CD", headers=_auth())
    assert resp.status_code == 200
    ids = [it["id"] for it in client.get("/exceptions", headers=_auth()).json()]
    assert "EXC-AB12CD" not in ids
    assert "EXC-0003" in ids


def test_delete_seed_item_forbidden() -> None:
    """The 66 committed human-test emails are the demo's substrate; keep them."""
    client = _app([_item("EXC-0003", 1.0)])
    resp = client.delete("/exceptions/EXC-0003", headers=_auth())
    assert resp.status_code == 403
    ids = [it["id"] for it in client.get("/exceptions", headers=_auth()).json()]
    assert "EXC-0003" in ids


def test_delete_missing_or_cross_org_is_404() -> None:
    from order_desk.api.auth import issue_token

    item = _item("EXC-AB12CD", 1.0)
    item.org_id = "org-a"
    client = _app([item])
    assert client.delete("/exceptions/nope", headers=_auth()).status_code == 404
    org_b = {"Authorization": f"Bearer {issue_token(SECRET, 'b', org_id='org-b')}"}
    assert client.delete("/exceptions/EXC-AB12CD", headers=org_b).status_code == 404


def test_extract_inbox_rejects_unknown_address() -> None:
    client = _mailbox_app([], live_extractor=_FakeRawExtractor())
    resp = client.post(
        "/exceptions/extract-inbox", headers=_auth(), json={"address": "other@example.com"}
    )
    assert resp.status_code == 400


def test_extract_inbox_503_without_imap_config() -> None:
    client = _app([])
    client.app.state.live_extractor = _FakeRawExtractor()
    resp = client.post(
        "/exceptions/extract-inbox", headers=_auth(), json={"address": "orders@example.com"}
    )
    assert resp.status_code == 503


def test_live_extract_503_when_not_configured() -> None:
    client = _app([_item("x", 5.0)])
    resp = client.post("/exceptions/extract", headers=_auth(), json={"subject": "s", "body": "b"})
    assert resp.status_code == 503


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
            "requested_date_text": "2026-08-01",
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


def test_approve_blocked_until_all_fields_present() -> None:
    """Every extraction field is required to approve; a gap returns 422."""
    item = _order_item("EXC-1", "small carton", 50)
    item.extraction["requested_date_text"] = None  # one missing field
    client, app = _app_with_fulfillment([item])
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.status_code == 422
    assert "requested_date_text" in str(resp.json()["detail"])
    assert len(app.state.order_sink.submitted) == 0
    # the item was not marked approved
    got = client.get("/exceptions/EXC-1", headers=_auth()).json()
    assert got["status"] == "pending"


def test_approve_allowed_once_edits_fill_the_gaps() -> None:
    item = _order_item("EXC-1", "small carton", 50)
    item.extraction["requested_date_text"] = None
    client, app = _app_with_fulfillment([item])
    client.post(
        "/exceptions/EXC-1/review",
        headers=_auth(),
        json={"action": "edited", "edits": {"requested_date_text": "2026-08-01"}},
    )
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.status_code == 200
    assert resp.json()["fulfillment"]["submitted"] is True


def test_missing_quantity_blocks_approve() -> None:
    item = _order_item("EXC-1", "small carton", None)
    client, _ = _app_with_fulfillment([item])
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.status_code == 422
    assert "line_items.0.quantity" in str(resp.json()["detail"])


def test_deleted_line_not_required() -> None:
    """A deleted line's empty fields must not block the approve."""
    item = _order_item("EXC-1", "small carton", 50)
    item.extraction["line_items"].append(
        {
            "product_text": "spurious",
            "quantity": None,
            "unit_text": None,
            "unit_price_text": None,
            "item_notes": None,
        }
    )
    client, app = _app_with_fulfillment([item])
    client.post(
        "/exceptions/EXC-1/review",
        headers=_auth(),
        json={"action": "edited", "edits": {"line_items.1": "__deleted__"}},
    )
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.status_code == 200
    assert len(app.state.order_sink.submitted) == 1


def test_routed_away_item_not_approvable_as_is() -> None:
    """No extraction means no order to send; approve must be blocked, not a no-op."""
    item = _order_item("EXC-1", "x", 1)
    item.extraction = None
    client, app = _app_with_fulfillment([item])
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.status_code == 422
    assert len(app.state.order_sink.submitted) == 0
    # reject remains the way to dismiss it
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "rejected", "edits": {}}
    )
    assert resp.status_code == 200


def test_reviewer_builds_order_on_routed_away_item() -> None:
    """The reviewer rescues a misrouted order by filling every field from scratch."""
    item = _order_item("EXC-1", "x", 1)
    item.extraction = None
    client, app = _app_with_fulfillment([item])
    client.post(
        "/exceptions/EXC-1/review",
        headers=_auth(),
        json={
            "action": "edited",
            "edits": {
                "customer_po_text": "PO-77",
                "delivery_address_text": "Botany",
                "buyer_name_text": "Dana",
                "requested_date_text": "2026-08-01",
                "line_items.0.product_text": "small carton",
                "line_items.0.quantity": "50",
            },
        },
    )
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.status_code == 200
    assert resp.json()["fulfillment"]["submitted"] is True
    assert len(app.state.order_sink.submitted) == 1
    assert app.state.order_sink.submitted[0].customer_po == "PO-77"


def test_order_with_no_lines_blocks_approve() -> None:
    """An order with zero line items must never reach the ERP."""
    item = _order_item("EXC-1", "small carton", 50)
    item.extraction["line_items"] = []
    client, app = _app_with_fulfillment([item])
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.status_code == 422
    assert "line_items" in str(resp.json()["detail"])
    assert len(app.state.order_sink.submitted) == 0


def test_reject_needs_no_fields() -> None:
    item = _order_item("EXC-1", "small carton", None)
    item.extraction["buyer_name_text"] = None
    client, _ = _app_with_fulfillment([item])
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "rejected", "edits": {}}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


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


def test_edited_save_does_not_fulfill() -> None:
    """Two-step flow: saving corrections records them; only Approve sends."""
    client, app = _app_with_fulfillment([_order_item("EXC-1", "small karton", 50)])
    resp = client.post(
        "/exceptions/EXC-1/review",
        headers=_auth(),
        json={"action": "edited", "edits": {"line_items.0.product_text": "small carton"}},
    )
    assert resp.json()["status"] == "edited"
    assert len(app.state.order_sink.submitted) == 0
    # approve sends the corrected version
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.json()["fulfillment"]["submitted"] is True
    assert len(app.state.order_sink.submitted) == 1
    assert app.state.order_sink.submitted[0].lines[0].sku  # resolved via the correction


def test_reapprove_after_new_edits_sends_amendment() -> None:
    """New corrections on an already-sent order go out as an amendment."""
    client, app = _app_with_fulfillment([_order_item("EXC-1", "small carton", 50)])
    first = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    ).json()
    client.post(
        "/exceptions/EXC-1/review",
        headers=_auth(),
        json={"action": "edited", "edits": {"delivery_address_text": "Eagle Farm"}},
    )
    second = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    ).json()
    assert len(app.state.order_sink.submitted) == 2
    assert app.state.order_sink.submitted[1].delivery_address == "Eagle Farm"
    assert app.state.order_sink.submitted[1].amends == first["fulfillment"]["order_id"]
    assert second["fulfillment"]["amends"] == first["fulfillment"]["order_id"]


def test_legacy_fulfillment_record_is_not_resubmitted() -> None:
    """A record from before for_edits existed must read as already-sent."""
    item = _order_item("EXC-1", "small carton", 50)
    item.status = ReviewStatus.APPROVED
    item.fulfillment = {
        "submitted": True,
        "order_id": "ORD-LEGACY",
        "reason": "submitted",
        "unresolved": [],
    }
    client, app = _app_with_fulfillment([item])
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.json()["fulfillment"]["order_id"] == "ORD-LEGACY"
    assert len(app.state.order_sink.submitted) == 0


def test_new_edits_on_legacy_record_reopen_fulfillment() -> None:
    """A legacy record covers the edits it was loaded with -- not later ones.

    Freezing it against whatever the edits currently are would make Approve
    dead forever on such items: new corrections could never go out.
    """
    item = _order_item("EXC-1", "small carton", 50)
    item.status = ReviewStatus.APPROVED
    item.fulfillment = {
        "submitted": True,
        "order_id": "ORD-LEGACY",
        "reason": "submitted",
        "unresolved": [],
    }
    client, app = _app_with_fulfillment([item])
    client.post(
        "/exceptions/EXC-1/review",
        headers=_auth(),
        json={"action": "edited", "edits": {"delivery_address_text": "Eagle Farm"}},
    )
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert len(app.state.order_sink.submitted) == 1
    assert resp.json()["fulfillment"]["amends"] == "ORD-LEGACY"


def test_second_approve_does_not_resubmit_to_erp() -> None:
    """Re-approving a fulfilled item returns the recorded receipt, not a new order.

    Without this, every approve click appends a duplicate order to the ERP.
    """
    client, app = _app_with_fulfillment([_order_item("EXC-1", "small carton", 50)])
    first = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    ).json()
    second = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    ).json()
    assert len(app.state.order_sink.submitted) == 1
    assert second["fulfillment"]["order_id"] == first["fulfillment"]["order_id"]


def test_fulfillment_survives_refresh() -> None:
    """GET after approve still carries the receipt, so the UI can show it."""
    client, _ = _app_with_fulfillment([_order_item("EXC-1", "small carton", 50)])
    client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    got = client.get("/exceptions/EXC-1", headers=_auth()).json()
    assert got["fulfillment"]["submitted"] is True
    assert got["fulfillment"]["order_id"] == "ORD-APITEST"


def test_held_order_retries_on_next_approve() -> None:
    """A held order never reached the ERP, so re-approving may retry it."""
    client, app = _app_with_fulfillment([_order_item("EXC-2", "mystery widget xyz", 50)])
    for _ in range(2):
        resp = client.post(
            "/exceptions/EXC-2/review", headers=_auth(), json={"action": "approved", "edits": {}}
        )
    assert resp.json()["fulfillment"]["reason"] == "held_for_mapping"
    assert len(app.state.order_sink.submitted) == 0
    assert len(app.state.notifier.sent) == 2  # fulfilment ran both times


def test_delete_spurious_line_then_approve_submits() -> None:
    """Removing a model-invented line item unblocks an otherwise-held order."""
    item = _order_item("EXC-1", "small carton", 50)
    item.extraction["line_items"].append(
        {
            "product_text": "4x6 ones",
            "quantity": None,
            "unit_text": None,
            "unit_price_text": None,
            "item_notes": None,
        }
    )
    client, app = _app_with_fulfillment([item])
    client.post(
        "/exceptions/EXC-1/review",
        headers=_auth(),
        json={"action": "edited", "edits": {"line_items.1": "__deleted__"}},
    )
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    assert resp.json()["fulfillment"]["submitted"] is True
    assert len(app.state.order_sink.submitted) == 1
    assert len(app.state.order_sink.submitted[0].lines) == 1


def test_held_response_carries_quantity_issues() -> None:
    """A hold caused by a quantity rule must say so, not hold silently."""
    client, app = _app_with_fulfillment([_order_item("EXC-1", "small carton", 1)])  # moq 25
    resp = client.post(
        "/exceptions/EXC-1/review", headers=_auth(), json={"action": "approved", "edits": {}}
    )
    f = resp.json()["fulfillment"]
    assert f["submitted"] is False
    assert f["unresolved"] == []
    assert any("below_moq" in issue for issue in f["issues"])
    assert len(app.state.order_sink.submitted) == 0


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
