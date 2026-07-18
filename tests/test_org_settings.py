"""Per-org settings: the Slack webhook a customer configures from the UI."""

from fastapi.testclient import TestClient

from order_desk.api.app import create_app
from order_desk.api.auth import issue_token
from order_desk.api.config import Settings
from order_desk.api.org_settings import JsonOrgSettings
from order_desk.api.review_store import InMemoryReviewStore
from order_desk.review.priority import ReviewItem, ReviewStatus

SECRET = "org-settings-test-secret-32-bytes-ok!"


def _order_item(id_, product_text, qty):
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


ADMIN_SCOPES = ["extract:write", "review:read", "review:write", "org:admin"]
REVIEWER_SCOPES = ["extract:write", "review:read", "review:write"]


def _client(items=None, org_settings=None):
    app = create_app(
        Settings(adapter_model="x", vllm_base_url="", vllm_api_key="EMPTY", jwt_secret=SECRET)
    )
    if items is not None:
        app.state.review_store = InMemoryReviewStore(items)
    if org_settings is not None:
        app.state.org_settings = org_settings
    return TestClient(app)


def _auth(scopes, org_id="org-a"):
    return {"Authorization": f"Bearer {issue_token(SECRET, 'u', org_id=org_id, scopes=scopes)}"}


def test_set_webhook_requires_admin_scope() -> None:
    client = _client()
    resp = client.put(
        "/org/slack-webhook",
        headers=_auth(REVIEWER_SCOPES),
        json={"url": "https://hooks.slack.com/services/T0/B0/x"},
    )
    assert resp.status_code == 403


def test_set_and_read_webhook_masked() -> None:
    client = _client()
    resp = client.put(
        "/org/slack-webhook",
        headers=_auth(ADMIN_SCOPES),
        json={"url": "https://hooks.slack.com/services/T0AAA/B0BBB/secretpart"},
    )
    assert resp.status_code == 200
    got = client.get("/org/slack-webhook", headers=_auth(REVIEWER_SCOPES)).json()
    assert got["configured"] is True
    assert "secretpart" not in str(got)  # never echo the full secret


def test_webhook_is_org_scoped() -> None:
    client = _client()
    client.put(
        "/org/slack-webhook",
        headers=_auth(ADMIN_SCOPES, org_id="org-a"),
        json={"url": "https://hooks.slack.com/services/T0/B0/a"},
    )
    got = client.get("/org/slack-webhook", headers=_auth(REVIEWER_SCOPES, org_id="org-b")).json()
    assert got["configured"] is False


def test_clear_webhook() -> None:
    client = _client()
    client.put(
        "/org/slack-webhook",
        headers=_auth(ADMIN_SCOPES),
        json={"url": "https://hooks.slack.com/services/T0/B0/a"},
    )
    client.put("/org/slack-webhook", headers=_auth(ADMIN_SCOPES), json={"url": ""})
    got = client.get("/org/slack-webhook", headers=_auth(ADMIN_SCOPES)).json()
    assert got["configured"] is False


def test_non_https_webhook_rejected() -> None:
    client = _client()
    resp = client.put(
        "/org/slack-webhook", headers=_auth(ADMIN_SCOPES), json={"url": "http://evil.example"}
    )
    assert resp.status_code == 400


def test_json_org_settings_persist(tmp_path) -> None:
    path = tmp_path / "org_settings.json"
    JsonOrgSettings(path).set_webhook("org-a", "https://hooks.slack.com/services/T0/B0/a")
    assert JsonOrgSettings(path).get_webhook("org-a") == "https://hooks.slack.com/services/T0/B0/a"
    assert JsonOrgSettings(path).get_webhook("org-b") == ""


def test_set_mailbox_requires_admin_scope() -> None:
    client = _client()
    resp = client.put(
        "/org/mailbox",
        headers=_auth(REVIEWER_SCOPES),
        json={"host": "imap.x.com", "address": "a@x.com", "password": "pw"},
    )
    assert resp.status_code == 403


def test_set_mailbox_never_echoes_password() -> None:
    client = _client()
    resp = client.put(
        "/org/mailbox",
        headers=_auth(ADMIN_SCOPES),
        json={"host": "imap.x.com", "address": "a@x.com", "password": "sekrit-pw"},
    )
    assert resp.status_code == 200
    got = client.get("/org/mailbox", headers=_auth(REVIEWER_SCOPES)).json()
    assert got["configured"] is True
    assert got["address"] == "a@x.com"
    assert got["host"] == "imap.x.com"
    assert "sekrit-pw" not in str(got)
    assert "sekrit-pw" not in str(resp.json())


def test_clear_mailbox() -> None:
    client = _client()
    client.put(
        "/org/mailbox",
        headers=_auth(ADMIN_SCOPES),
        json={"host": "imap.x.com", "address": "a@x.com", "password": "pw"},
    )
    client.put(
        "/org/mailbox",
        headers=_auth(ADMIN_SCOPES),
        json={"host": "", "address": "", "password": ""},
    )
    assert client.get("/org/mailbox", headers=_auth(ADMIN_SCOPES)).json()["configured"] is False


class _CapturingImap:
    """Fake IMAP4_SSL: one unseen message; records connection credentials."""

    seen: list[tuple] = []

    def __init__(self, host):
        _CapturingImap.seen.append(("host", host))

    def login(self, user, password):
        _CapturingImap.seen.append(("login", user, password))
        return "OK", []

    def select(self, mailbox):
        return "OK", []

    def search(self, charset, criteria):
        return "OK", [b"1"]

    def fetch(self, num, parts):
        return "OK", [(b"1 (RFC822 {10}", b"Subject: s\r\n\r\nbody"), b")"]

    def logout(self):
        return "BYE", []


class _FakeRawExtractor:
    def extract_raw(self, raw, item_id):
        return ReviewItem(
            id=item_id,
            subject="s",
            body=raw,
            extraction=None,
            field_flags=[],
            asks=[],
            violations=[],
            priority=0.0,
        )


def test_extract_inbox_uses_org_mailbox(monkeypatch) -> None:
    """One-click extract: an empty request pulls the org's configured mailbox."""
    import imaplib

    monkeypatch.setattr(imaplib, "IMAP4_SSL", _CapturingImap)
    _CapturingImap.seen.clear()
    client = _client(items=[])
    client.app.state.live_extractor = _FakeRawExtractor()
    client.put(
        "/org/mailbox",
        headers=_auth(ADMIN_SCOPES),
        json={"host": "imap.org-mail.com", "address": "orders@org.com", "password": "org-pw"},
    )
    resp = client.post("/exceptions/extract-inbox", headers=_auth(REVIEWER_SCOPES), json={})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert ("host", "imap.org-mail.com") in _CapturingImap.seen
    assert ("login", "orders@org.com", "org-pw") in _CapturingImap.seen


def test_extract_inbox_empty_request_without_any_mailbox_503() -> None:
    client = _client(items=[])
    client.app.state.live_extractor = _FakeRawExtractor()
    resp = client.post("/exceptions/extract-inbox", headers=_auth(REVIEWER_SCOPES), json={})
    assert resp.status_code == 503


def test_submitted_with_no_channel_says_so() -> None:
    """No org webhook and no global one: the receipt must not stay silent about
    the fact that nobody was notified."""
    from order_desk.fulfillment.notify import MockNotifier

    item = _order_item("EXC-1", "small carton", 50)
    item.org_id = "org-a"
    client = _client(items=[item])

    class FakeSink:
        def submit(self, order):
            from order_desk.fulfillment.erp import OrderReceipt

            return OrderReceipt(
                order_id="ORD-QUIET",
                status="accepted",
                submitted_at="2026-01-01T00:00:00Z",
                total_cents=1,
            )

    client.app.state.order_sink = FakeSink()
    client.app.state.notifier = MockNotifier()  # what build_notifier("") yields

    resp = client.post(
        "/exceptions/EXC-1/review",
        headers=_auth(REVIEWER_SCOPES, org_id="org-a"),
        json={"action": "approved", "edits": {}},
    )
    f = resp.json()["fulfillment"]
    assert f["submitted"] is True
    assert f["notify_error"] == "no notification channel configured"


def test_approve_notifies_org_webhook_and_failure_keeps_receipt() -> None:
    """The org's own webhook is used at approve time; a notification failure
    must not void the ERP receipt (the order IS in the sink)."""
    from order_desk.api.org_settings import InMemoryOrgSettings
    from order_desk.fulfillment.notify import MockNotifier

    item = _order_item("EXC-1", "small carton", 50)
    item.org_id = "org-a"
    client = _client(items=[item])
    settings = InMemoryOrgSettings()
    # unreachable host: connection fails when fulfilment tries to notify
    settings.set_webhook("org-a", "https://slack.invalid.localdomain/hook")
    client.app.state.org_settings = settings

    class FakeSink:
        def __init__(self):
            self.submitted = []

        def submit(self, order):
            from order_desk.fulfillment.erp import OrderReceipt

            self.submitted.append(order)
            return OrderReceipt(
                order_id="ORD-ORGHOOK",
                status="accepted",
                submitted_at="2026-01-01T00:00:00Z",
                total_cents=1,
            )

    client.app.state.order_sink = FakeSink()
    client.app.state.notifier = MockNotifier()  # global fallback, must NOT be used

    resp = client.post(
        "/exceptions/EXC-1/review",
        headers=_auth(REVIEWER_SCOPES, org_id="org-a"),
        json={"action": "approved", "edits": {}},
    )
    data = resp.json()
    assert data["fulfillment"]["submitted"] is True
    assert data["fulfillment"]["order_id"] == "ORD-ORGHOOK"
    assert data["fulfillment"]["notify_error"]  # the failed webhook is reported
    assert len(client.app.state.order_sink.submitted) == 1
    assert client.app.state.notifier.sent == []  # org webhook took precedence
