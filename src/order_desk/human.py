"""Human-authored OOD slice: authoring parser, contracts, freeze (step 1.8c).

The slice measures distribution shift for the deep component: order emails
written by a person against the same fixtures, in their own words. Machine
contracts are deliberately weaker than the synthetic renderer's: verbatim
containment of every gold string still holds, checked against the
subject+body union (real mail legitimately carries content in the subject),
but the digit/term closures do not apply -- those existed to stop a template
renderer from polluting gold, and here the author *is* the distribution.

gold quantity is an int, so number words in prose ("one carton") cannot be
machine-checked against it; quantity correctness is authorial, consistent
with the audit protocol treating the human as ground-truth authority.

Records carry the same 11 keys as synthetic records, with oracle / render /
scenario as null. The routing oracle for human records is derived at eval
time by the Phase 5 validator (validator(gold, sender)) and never stored:
storing it now would mean a second oracle implementation free to drift from
the runtime one.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from order_desk.customers import CustomerBook, load_customers
from order_desk.schemas import EmailClass, ExtractedOrder

HUMAN_ID_RE = re.compile(r"^### (HUM-\d{4})\s*$")
CORPUS_TZ = ZoneInfo("Australia/Sydney")
GOLD_CLASSES = frozenset({EmailClass.NEW_ORDER, EmailClass.AMENDMENT})


class AuthoringError(ValueError):
    """The authoring file violates the format or a contract."""


def gold_surfaces(gold: ExtractedOrder) -> list[str]:
    """Every string field that must appear verbatim in subject+body."""
    surfaces = [
        gold.customer_po_text,
        gold.requested_date_text,
        gold.delivery_address_text,
        gold.buyer_name_text,
        gold.notes,
    ]
    for item in gold.line_items:
        surfaces += [item.product_text, item.unit_text, item.unit_price_text, item.item_notes]
    return [s for s in surfaces if s is not None]


def _verify_union_containment(record_id: str, subject: str, body: str, surfaces: list[str]) -> None:
    hay_base = subject + "\n" + body
    pool = set(surfaces)
    for surface in pool:
        hay = hay_base
        shadows = [t for t in pool if t != surface and surface in t]
        for shadow in sorted(shadows, key=len, reverse=True):
            hay = hay.replace(shadow, "\ufffd")
        if surface not in hay:
            raise AuthoringError(
                f"{record_id}: gold surface {surface!r} not found verbatim in "
                "subject or body (surfaces must not wrap across lines)"
            )


def _parse_header(record_id: str, lineno: int, label: str, line: str) -> str:
    prefix = f"{label}: "
    if not line.startswith(prefix):
        raise AuthoringError(
            f"line {lineno}: expected '{label}: ...' in block {record_id}, got {line!r}"
        )
    value = line[len(prefix) :].strip()
    if not value:
        raise AuthoringError(f"line {lineno}: empty {label} in block {record_id}")
    return value


def _parse_block(start_lineno: int, lines: list[str], book: CustomerBook) -> dict[str, Any]:
    match = HUMAN_ID_RE.match(lines[0])
    if match is None:
        raise AuthoringError(
            f"line {start_lineno}: block header must be '### HUM-NNNN', got {lines[0]!r}"
        )
    rid = match.group(1)
    if len(lines) < 6:
        raise AuthoringError(f"{rid}: block is truncated")
    sender = _parse_header(rid, start_lineno + 1, "From", lines[1]).lower()
    sent_raw = _parse_header(rid, start_lineno + 2, "Sent", lines[2])
    class_raw = _parse_header(rid, start_lineno + 3, "Class", lines[3])
    subject = _parse_header(rid, start_lineno + 4, "Subject", lines[4])

    try:
        email_class = EmailClass(class_raw)
    except ValueError as exc:
        raise AuthoringError(f"{rid}: unknown class {class_raw!r}") from exc
    try:
        naive = datetime.strptime(sent_raw, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise AuthoringError(f"{rid}: Sent must be 'YYYY-MM-DD HH:MM', got {sent_raw!r}") from exc
    if naive.year != 2026:
        raise AuthoringError(f"{rid}: keep Sent within the corpus year 2026")
    sent_at = naive.replace(tzinfo=CORPUS_TZ)
    if lines[5].strip():
        raise AuthoringError(f"{rid}: expected a blank line after Subject")

    body_lines: list[str] = []
    gold_lines: list[str] | None = None
    i = 6
    while i < len(lines):
        if lines[i].strip() == "```gold":
            i += 1
            gold_lines = []
            while i < len(lines) and lines[i].strip() != "```":
                gold_lines.append(lines[i])
                i += 1
            if i == len(lines):
                raise AuthoringError(f"{rid}: gold fence never closes")
            i += 1
            for j in range(i, len(lines)):
                if lines[j].strip():
                    raise AuthoringError(
                        f"{rid}: unexpected content after the gold fence: {lines[j]!r}"
                    )
            break
        body_lines.append(lines[i])
        i += 1
    body = "\n".join(body_lines).strip()
    if not body:
        raise AuthoringError(f"{rid}: body is empty")
    body += "\n"

    customer = book.resolve_customer(sender)
    if customer is None and email_class is not EmailClass.OTHER:
        raise AuthoringError(f"{rid}: sender {sender!r} does not resolve to a fixture customer")

    gold: ExtractedOrder | None = None
    if email_class in GOLD_CLASSES:
        if gold_lines is None:
            raise AuthoringError(f"{rid}: class {email_class.value} requires a ```gold fence")
        try:
            gold = ExtractedOrder.model_validate_json("\n".join(gold_lines))
        except ValidationError as exc:
            raise AuthoringError(f"{rid}: gold violates the extraction contract: {exc}") from exc
        if email_class is EmailClass.NEW_ORDER and not gold.line_items:
            raise AuthoringError(f"{rid}: a new_order needs at least one line item")
        _verify_union_containment(rid, subject, body, gold_surfaces(gold))
    elif gold_lines is not None:
        raise AuthoringError(f"{rid}: class {email_class.value} must not carry a gold fence")

    return {
        "id": rid,
        "email_class": email_class.value,
        "subject": subject,
        "body": body,
        "sender_email": sender,
        "sent_at": sent_at.isoformat(),
        "customer_id": customer.customer_id if customer is not None else None,
        "gold_extraction": gold.model_dump() if gold is not None else None,
        "oracle": None,
        "render": None,
        "scenario": None,
    }


def parse_authoring(text: str, book: CustomerBook | None = None) -> list[dict[str, Any]]:
    """Parse the authoring file into frozen-record dicts, enforcing contracts."""
    book = book or load_customers()
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("### ")]
    if not starts:
        raise AuthoringError("no '### HUM-NNNN' blocks found")
    records = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        records.append(_parse_block(start + 1, lines[start:end], book))
    ids = [record["id"] for record in records]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise AuthoringError(f"duplicate ids: {', '.join(dupes)}")
    return records
