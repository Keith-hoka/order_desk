from pathlib import Path

from order_desk.ingest.pack import (
    pack_faithful,
    pack_html,
    pack_reply,
    pack_with_signature,
)
from order_desk.ingest.run import process_raw, process_source
from order_desk.ingest.source import EmlDirectorySource, ImapSource
from order_desk.ingest.standardize import REPLY_HISTORY_ASK, standardize_email
from order_desk.pipeline.graph import build_graph
from order_desk.pipeline.policy import Classification, RouteDecision
from order_desk.schemas import EmailClass, ExtractedOrder

# a realistic order record (human-style)
RECORD = {
    "id": "HUM-TEST-1",
    "subject": "Packing tape reorder - PO-73218",
    "body": "Good morning,\n\nWe would like to reorder 72 rolls of clear packing tape "
    "for our Botany warehouse. Please book this against PO-73218.\n\nKind regards, Dana",
    "sender_email": "dana@harbourline.com.au",
    "sent_at": "Mon, 5 May 2026 09:00:00 +1000",
}

ORDER = ExtractedOrder(
    customer_po_text="PO-73218",
    requested_date_text=None,
    delivery_address_text="Botany",
    buyer_name_text="Dana",
    notes=None,
    line_items=[
        {
            "product_text": "clear packing tape",
            "quantity": 72,
            "unit_text": "rolls",
            "unit_price_text": None,
            "item_notes": None,
        }
    ],
)


def _fake_classifier(cls):
    def _c(subject, body):
        return Classification(email_class=cls, confidence=0.95)

    return _c


def _fake_extractor():
    def _e(subject, body):
        return ORDER, {"customer_po_text": 0.9}

    return _e


def _fake_app():
    return build_graph(_fake_classifier(EmailClass.NEW_ORDER), _fake_extractor())


# --- packing round-trips through standardization ---


def test_faithful_pack_preserves_body() -> None:
    std = standardize_email(pack_faithful(RECORD))
    assert std.subject == "Packing tape reorder - PO-73218"
    assert "72 rolls of clear packing tape" in std.body
    assert std.is_reply is False


def test_signature_pack_gets_stripped() -> None:
    std = standardize_email(pack_with_signature(RECORD))
    assert "72 rolls" in std.body
    assert "confidential" not in std.body.lower()  # signature removed
    assert "HarbourLine" not in std.body


def test_html_pack_converted() -> None:
    std = standardize_email(pack_html(RECORD))
    assert "72 rolls of clear packing tape" in std.body
    assert "<p>" not in std.body


def test_reply_pack_flags_history_when_short() -> None:
    short = dict(RECORD, body="72 rolls please.")
    std = standardize_email(pack_reply(short, "How many rolls?", "<q-1@x.com>"))
    assert std.is_reply is True
    assert std.in_reply_to == "<q-1@x.com>"
    assert "72 rolls" in std.body
    assert "How many rolls" not in std.body  # quoted question stripped
    assert REPLY_HISTORY_ASK in std.asks


# --- EmailSource ---


def test_eml_directory_source(tmp_path: Path) -> None:
    (tmp_path / "a.eml").write_text(pack_faithful(RECORD), encoding="utf-8")
    (tmp_path / "b.eml").write_text(pack_faithful(dict(RECORD, subject="second")), encoding="utf-8")
    source = EmlDirectorySource(tmp_path)
    raws = list(source.fetch())
    assert len(raws) == 2


class _FakeImap:
    """Stands in for imaplib.IMAP4_SSL: two unseen messages."""

    instances: list["_FakeImap"] = []

    def __init__(self, host: str) -> None:
        self.host = host
        self.calls: list[tuple] = []
        _FakeImap.instances.append(self)

    def login(self, user, password):
        self.calls.append(("login", user, password))
        return "OK", []

    def select(self, mailbox):
        self.calls.append(("select", mailbox))
        return "OK", []

    def search(self, charset, criteria):
        self.calls.append(("search", charset, criteria))
        return "OK", [b"1 3"]

    def fetch(self, num, parts):
        self.calls.append(("fetch", num, parts))
        raw = f"Subject: msg-{num.decode()}\r\n\r\nbody {num.decode()}".encode()
        return "OK", [(b"1 (RFC822 {42}", raw), b")"]

    def logout(self):
        self.calls.append(("logout",))
        return "BYE", []


def test_imap_source_limit_takes_most_recent(monkeypatch) -> None:
    import imaplib

    _FakeImap.instances.clear()
    monkeypatch.setattr(imaplib, "IMAP4_SSL", _FakeImap)
    source = ImapSource("imap.example.com", "user", "pw")
    raws = list(source.fetch(limit=1))
    assert len(raws) == 1
    assert "Subject: msg-3" in raws[0]  # highest sequence number = most recent


def test_imap_source_fetches_unseen(monkeypatch) -> None:
    import imaplib

    _FakeImap.instances.clear()
    monkeypatch.setattr(imaplib, "IMAP4_SSL", _FakeImap)
    source = ImapSource("imap.example.com", "user", "pw", mailbox="INBOX")
    raws = list(source.fetch())
    assert len(raws) == 2
    assert "Subject: msg-1" in raws[0]
    assert "Subject: msg-3" in raws[1]
    fake = _FakeImap.instances[0]
    assert ("login", "user", "pw") in fake.calls
    assert ("select", "INBOX") in fake.calls
    assert ("search", None, "UNSEEN") in fake.calls
    assert fake.calls[-1] == ("logout",)  # always logs out


# --- ingest -> pipeline ---


def test_process_raw_runs_pipeline() -> None:
    state = process_raw(_fake_app(), pack_faithful(RECORD))
    assert state.route == RouteDecision.EXTRACT
    assert state.extraction is not None
    assert state.extraction.customer_po_text == "PO-73218"


def test_process_raw_merges_history_ask() -> None:
    short = dict(RECORD, body="72 rolls please.")
    state = process_raw(_fake_app(), pack_reply(short, "How many rolls?", "<q-1@x.com>"))
    # both the standardization ask and any pipeline ask are present
    assert REPLY_HISTORY_ASK in state.asks


def test_process_source_over_directory(tmp_path: Path) -> None:
    (tmp_path / "a.eml").write_text(pack_faithful(RECORD), encoding="utf-8")
    (tmp_path / "b.eml").write_text(pack_with_signature(RECORD), encoding="utf-8")
    states = process_source(_fake_app(), EmlDirectorySource(tmp_path))
    assert len(states) == 2
    assert all(s.extraction is not None for s in states)
