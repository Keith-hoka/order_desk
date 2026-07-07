"""Standardize raw email into clean (subject, body) for the pipeline (Phase 6).

Real email is RFC 822/MIME -- headers, multipart, HTML, signatures, quoted
reply chains -- while the pipeline expects a clean (subject, body). This layer
parses the message, chooses a text body (text/plain preferred, else text/html
converted), strips signatures and quoted history, and preserves threading
metadata (In-Reply-To / References) without folding it into the body.

Threading policy (decision A): extraction uses the latest single message with
quoted history removed. Order conversations are incremental -- a reply may
carry only "50 boxes" while the product sits in an earlier message -- so a
reply-shaped message (short body, In-Reply-To present) is flagged with an ask
rather than silently extracted from partial context. The fine-tune was trained
on self-contained single emails; multi-turn aggregation is a known boundary,
surfaced as a reviewable exception, not faked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from email.message import Message
from email.parser import Parser
from email.policy import default as default_policy

REPLY_HISTORY_ASK = (
    "email is a reply; order details may be in the conversation history "
    "not included here -- review against the thread"
)

# Quoted-history markers: everything from these lines onward is prior context.
_QUOTE_MARKERS = [
    re.compile(r"^On .*wrote:$", re.MULTILINE),
    re.compile(r"^-+\s*Original Message\s*-+$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^_{5,}$", re.MULTILINE),
    re.compile(r"^From:.*$", re.MULTILINE),  # forwarded/quoted header block
]

# Signature markers: everything from these onward is a signature/footer.
_SIGNATURE_MARKERS = [
    re.compile(r"^-- $", re.MULTILINE),  # RFC 3676 signature delimiter
    re.compile(r"^Sent from my \w+", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^Get Outlook for \w+", re.MULTILINE | re.IGNORECASE),
]


@dataclass
class StandardizedEmail:
    subject: str
    body: str
    sender: str
    date: str
    in_reply_to: str | None = None
    references: list[str] = field(default_factory=list)
    is_reply: bool = False
    asks: list[str] = field(default_factory=list)


def _html_to_text(html: str) -> str:
    import html2text

    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0  # no hard wrapping
    return h.handle(html)


def _extract_body(msg: Message) -> str:
    """Prefer text/plain; fall back to text/html converted to text."""
    plain: str | None = None
    html: str | None = None
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and plain is None:
                plain = part.get_content()
            elif ctype == "text/html" and html is None:
                html = part.get_content()
    else:
        content = msg.get_content()
        if msg.get_content_type() == "text/html":
            html = content
        else:
            plain = content
    if plain is not None and plain.strip():
        return plain
    if html is not None:
        return _html_to_text(html)
    return ""


def _strip_at_first_marker(text: str, markers: list[re.Pattern[str]]) -> str:
    """Cut the text at the earliest marker match; keep everything before it."""
    cut = len(text)
    for pattern in markers:
        m = pattern.search(text)
        if m is not None:
            cut = min(cut, m.start())
    return text[:cut]


def _strip_quoted_lines(text: str) -> str:
    """Drop trailing block of '>' quoted lines."""
    lines = text.splitlines()
    # remove trailing quoted lines and the blank lines around them
    while lines and (lines[-1].startswith(">") or not lines[-1].strip()):
        lines.pop()
    return "\n".join(lines)


def clean_body(raw_body: str) -> str:
    """Remove quoted history and signature; normalize whitespace."""
    body = _strip_at_first_marker(raw_body, _QUOTE_MARKERS)
    body = _strip_at_first_marker(body, _SIGNATURE_MARKERS)
    body = _strip_quoted_lines(body)
    # collapse 3+ blank lines to one, trim
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body


def standardize_email(raw: str) -> StandardizedEmail:
    """Parse a raw RFC 822 message string into a StandardizedEmail."""
    msg = Parser(policy=default_policy).parsestr(raw)
    subject = str(msg.get("subject", "")).strip()
    sender = str(msg.get("from", "")).strip()
    date = str(msg.get("date", "")).strip()
    in_reply_to = msg.get("in-reply-to")
    in_reply_to = str(in_reply_to).strip() if in_reply_to else None
    refs_raw = msg.get("references")
    references = str(refs_raw).split() if refs_raw else []

    raw_body = _extract_body(msg)
    body = clean_body(raw_body)

    is_reply = in_reply_to is not None or subject.lower().startswith("re:")
    asks: list[str] = []
    # A reply with a short body likely relies on conversation history.
    if is_reply and len(body.split()) < 25:
        asks.append(REPLY_HISTORY_ASK)

    return StandardizedEmail(
        subject=subject,
        body=body,
        sender=sender,
        date=date,
        in_reply_to=in_reply_to,
        references=references,
        is_reply=is_reply,
        asks=asks,
    )
