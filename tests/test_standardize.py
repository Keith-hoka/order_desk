from order_desk.ingest.standardize import (
    REPLY_HISTORY_ASK,
    clean_body,
    standardize_email,
)


def _eml(headers: dict[str, str], body: str, content_type: str = "text/plain") -> str:
    lines = [f"{k}: {v}" for k, v in headers.items()]
    lines.append(f"Content-Type: {content_type}; charset=utf-8")
    lines.append("")
    lines.append(body)
    return "\n".join(lines)


def test_parses_plain_headers_and_body() -> None:
    raw = _eml(
        {
            "Subject": "Packing tape reorder",
            "From": "dana@harbourline.com.au",
            "Date": "Mon, 5 May 2026 09:00:00 +1000",
        },
        "Please send 72 rolls of clear packing tape to Botany. PO-73218.",
    )
    email = standardize_email(raw)
    assert email.subject == "Packing tape reorder"
    assert email.sender == "dana@harbourline.com.au"
    assert "72 rolls" in email.body
    assert email.is_reply is False
    assert email.asks == []


def test_strips_signature() -> None:
    body = (
        "Please send 20 boxes of gloves.\n\n-- \nDana Whitfield\nHarbourLine Pty Ltd\n0400 123 456"
    )
    cleaned = clean_body(body)
    assert "20 boxes of gloves" in cleaned
    assert "Dana Whitfield" not in cleaned
    assert "0400 123 456" not in cleaned


def test_strips_sent_from_iphone() -> None:
    body = "Yes please proceed with the order.\n\nSent from my iPhone"
    cleaned = clean_body(body)
    assert "proceed with the order" in cleaned
    assert "iPhone" not in cleaned


def test_strips_quoted_reply_history() -> None:
    body = (
        "Yes, 50 boxes is correct.\n\n"
        "On Mon, 5 May 2026, Sales wrote:\n"
        "> How many boxes did you need?\n"
        "> Let us know."
    )
    cleaned = clean_body(body)
    assert "50 boxes is correct" in cleaned
    assert "How many boxes" not in cleaned


def test_strips_original_message_block() -> None:
    body = (
        "Confirmed, ship to the new address.\n\n"
        "-----Original Message-----\n"
        "From: sales@supplier.com\n"
        "Subject: RE: order"
    )
    cleaned = clean_body(body)
    assert "ship to the new address" in cleaned
    assert "Original Message" not in cleaned


def test_html_body_converted_to_text() -> None:
    raw = _eml(
        {"Subject": "order", "From": "a@b.com"},
        "<html><body><p>Please send <b>30 cartons</b> of bubble wrap.</p></body></html>",
        content_type="text/html",
    )
    email = standardize_email(raw)
    assert "30 cartons" in email.body
    assert "<b>" not in email.body
    assert "<p>" not in email.body


def test_reply_with_short_body_gets_history_ask() -> None:
    raw = _eml(
        {"Subject": "Re: quantity", "From": "c@d.com", "In-Reply-To": "<msg-123@supplier.com>"},
        "50 boxes please.",
    )
    email = standardize_email(raw)
    assert email.is_reply is True
    assert email.in_reply_to == "<msg-123@supplier.com>"
    assert REPLY_HISTORY_ASK in email.asks  # short reply -> flag for history


def test_reply_with_full_body_no_ask() -> None:
    raw = _eml(
        {"Subject": "Re: order", "From": "c@d.com", "In-Reply-To": "<m@x.com>"},
        "Following up on our call: please send 40 rolls of stretch film and "
        "30 boxes of mailers to the Eagle Farm depot against PO-9981, delivery "
        "next Tuesday if possible.",
    )
    email = standardize_email(raw)
    assert email.is_reply is True
    assert email.asks == []  # long enough to be self-contained


def test_references_parsed() -> None:
    raw = _eml(
        {
            "Subject": "Re: order",
            "From": "c@d.com",
            "References": "<m1@x.com> <m2@x.com> <m3@x.com>",
        },
        "Confirmed, proceed with all items as discussed in the thread above please.",
    )
    email = standardize_email(raw)
    assert email.references == ["<m1@x.com>", "<m2@x.com>", "<m3@x.com>"]
