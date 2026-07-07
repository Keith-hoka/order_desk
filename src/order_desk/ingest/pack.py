"""Pack human-authored records into .eml files for ingest testing (Phase 6).

The human slice is realistic hand-written content; wrapping it as RFC 822
gives the standardization layer realistic input with real email structure.
Mix (decision ii): most records are packed faithfully (to prove
standardization does not damage clean content), a few get realistic noise --
signatures, HTML bodies, and a constructed reply that quotes prior context --
to exercise stripping and the reply-history ask.
"""

from __future__ import annotations

from email.message import EmailMessage
from email.utils import format_datetime, parsedate_to_datetime

_SIGNATURE = "\n\n-- \n{name}\n{company}\nThis email and any attachments are confidential."


def _base_message(record: dict, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = record["subject"]
    msg["From"] = record["sender_email"]
    msg["To"] = "orders@meridianpackaging.example"
    try:
        msg["Date"] = format_datetime(parsedate_to_datetime(record["sent_at"]))
    except (TypeError, ValueError):
        msg["Date"] = record["sent_at"]
    msg["Message-ID"] = f"<{record['id']}@harbourline.example>"
    return msg


def pack_faithful(record: dict) -> str:
    msg = _base_message(record, record["body"])
    msg.set_content(record["body"])
    return msg.as_string()


def pack_with_signature(record: dict, name: str = "Dana", company: str = "HarbourLine") -> str:
    body = record["body"] + _SIGNATURE.format(name=name, company=company)
    msg = _base_message(record, body)
    msg.set_content(body)
    return msg.as_string()


def pack_html(record: dict) -> str:
    paragraphs = "".join(f"<p>{line}</p>" for line in record["body"].split("\n\n") if line.strip())
    html = f"<html><body>{paragraphs}</body></html>"
    msg = _base_message(record, record["body"])
    msg.set_content(html, subtype="html")
    return msg.as_string()


def pack_reply(record: dict, quoted_question: str, in_reply_to: str) -> str:
    """Construct a reply that answers a prior question, quoting it below."""
    body = (
        record["body"]
        + f"\n\nOn Mon, 5 May 2026, Sales wrote:\n> {quoted_question}\n> Let us know."
    )
    msg = _base_message(record, body)
    msg["In-Reply-To"] = in_reply_to
    msg["References"] = in_reply_to
    msg.replace_header("Subject", "Re: " + record["subject"])
    msg.set_content(body)
    return msg.as_string()
