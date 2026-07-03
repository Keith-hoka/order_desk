import json
from pathlib import Path

import pytest

from order_desk.human import AuthoringError, parse_authoring
from order_desk.materialize import sha256_of, to_jsonl

ROOT = Path(__file__).resolve().parent.parent
HUMAN_TEST = ROOT / "data" / "human" / "test_human.jsonl"
HUMAN_MANIFEST = ROOT / "data" / "human" / "MANIFEST.json"
AUTHORING = ROOT / "data" / "human" / "authoring.md"

FIXTURE = """# scratch notes (ignored by the parser)

### HUM-0001
From: dana.whitfield@harbourline.com.au
Sent: 2026-02-11 09:15
Class: new_order
Subject: Tape and satchels for Botany

Dana here - we're down to the last box of tape.

Can you send 6 rolls of that clear packing tape and one carton of poly mailers
to the Botany warehouse? PO to follow, sorry.

Thanks,
Dana

```gold
{
  "customer_po_text": null,
  "requested_date_text": null,
  "delivery_address_text": "Botany warehouse",
  "buyer_name_text": "Dana",
  "notes": null,
  "line_items": [
    {"product_text": "clear packing tape", "quantity": 6, "unit_text": "rolls",
     "unit_price_text": null, "item_notes": null},
    {"product_text": "poly mailers", "quantity": 1, "unit_text": "carton",
     "unit_price_text": null, "item_notes": null}
  ]
}
```

### HUM-0002
From: josh@fernvalenurseries.com.au
Sent: 2026-03-03 14:40
Class: inquiry
Subject: freight to regional QLD?

Hey - before I place anything, what's freight like out to Fernvale
these days? Same courier as last year?

Cheers,
Josh
"""

SUBJECT_PO_BLOCK = """### HUM-0003
From: marcus.yeo@redgumfurniture.com.au
Sent: 2026-04-06 10:05
Class: new_order
Subject: PO 4512345678 - pallets

Need 20 euro pallets for Dandenong please.

Regards,
Marcus

```gold
{
  "customer_po_text": "4512345678",
  "requested_date_text": null,
  "delivery_address_text": "Dandenong",
  "buyer_name_text": "Marcus",
  "notes": null,
  "line_items": [
    {"product_text": "euro pallets", "quantity": 20, "unit_text": null,
     "unit_price_text": null, "item_notes": null}
  ]
}
```
"""

OTHER_BLOCK = """### HUM-0004
From: promo@shinymail.co
Sent: 2026-05-01 11:00
Class: other
Subject: grow your revenue

We help wholesalers reach more buyers. Fancy a chat?

Best,
Shiny Mail
"""


def test_fixture_parses_shapes_and_localizes() -> None:
    records = parse_authoring(FIXTURE)
    assert [r["id"] for r in records] == ["HUM-0001", "HUM-0002"]
    assert [r["email_class"] for r in records] == ["new_order", "inquiry"]
    first, second = records
    assert first["customer_id"] == "CUST-0001"
    assert first["sent_at"].endswith("+11:00")
    assert first["body"].endswith("\n")
    assert set(first) == {
        "id",
        "email_class",
        "subject",
        "body",
        "sender_email",
        "sent_at",
        "customer_id",
        "gold_extraction",
        "oracle",
        "render",
        "scenario",
    }
    assert first["oracle"] is None and first["render"] is None and first["scenario"] is None
    assert second["gold_extraction"] is None


def test_union_containment_allows_subject_only_po() -> None:
    record = parse_authoring(SUBJECT_PO_BLOCK)[0]
    assert record["gold_extraction"]["customer_po_text"] == "4512345678"
    assert record["customer_id"] == "CUST-0002"


def test_containment_failure_pinpoints_id() -> None:
    broken = FIXTURE.replace('"Botany warehouse"', '"Botany depot"')
    with pytest.raises(AuthoringError, match="HUM-0001.*Botany depot"):
        parse_authoring(broken)


def test_gold_presence_rules_by_class() -> None:
    inquiry_with_gold = FIXTURE.rstrip() + (
        "\n\n```gold\n"
        '{"customer_po_text": null, "requested_date_text": null,\n'
        ' "delivery_address_text": null, "buyer_name_text": null,\n'
        ' "notes": null, "line_items": []}\n'
        "```\n"
    )
    with pytest.raises(AuthoringError, match="HUM-0002.*must not carry"):
        parse_authoring(inquiry_with_gold)
    no_gold = FIXTURE.split("```gold")[0]
    with pytest.raises(AuthoringError, match="HUM-0001.*requires"):
        parse_authoring(no_gold)


def test_unknown_sender_rules() -> None:
    record = parse_authoring(OTHER_BLOCK)[0]
    assert record["customer_id"] is None
    as_order = OTHER_BLOCK.replace("Class: other", "Class: new_order")
    with pytest.raises(AuthoringError, match="HUM-0004.*does not resolve"):
        parse_authoring(as_order)


def test_new_order_requires_line_item() -> None:
    empty_items = SUBJECT_PO_BLOCK.replace(
        '"line_items": [\n    {"product_text": "euro pallets", "quantity": 20, '
        '"unit_text": null,\n     "unit_price_text": null, "item_notes": null}\n  ]',
        '"line_items": []',
    )
    with pytest.raises(AuthoringError, match="HUM-0003.*at least one line item"):
        parse_authoring(empty_items)


def test_strict_gold_contract_surfaces_id() -> None:
    broken = FIXTURE.replace('"quantity": 6', '"quantity": "6"')
    with pytest.raises(AuthoringError, match="HUM-0001.*contract"):
        parse_authoring(broken)


def test_header_error_pinpoints_line() -> None:
    broken = FIXTURE.replace("Sent: 2026-02-11 09:15", "Date: 2026-02-11 09:15")
    with pytest.raises(AuthoringError, match="line 5.*Sent"):
        parse_authoring(broken)


def test_duplicate_ids_rejected() -> None:
    broken = FIXTURE.replace("### HUM-0002", "### HUM-0001")
    with pytest.raises(AuthoringError, match="duplicate ids: HUM-0001"):
        parse_authoring(broken)


def test_year_guard() -> None:
    broken = FIXTURE.replace("Sent: 2026-02-11 09:15", "Sent: 2025-02-11 09:15")
    with pytest.raises(AuthoringError, match="HUM-0001.*corpus year"):
        parse_authoring(broken)


def test_empty_body_and_trailing_junk() -> None:
    headers_only = (
        "### HUM-0009\nFrom: josh@fernvalenurseries.com.au\nSent: 2026-06-01 09:00\n"
        "Class: inquiry\nSubject: hi\n\n\n"
    )
    with pytest.raises(AuthoringError, match="HUM-0009.*body is empty"):
        parse_authoring(headers_only)
    junk = SUBJECT_PO_BLOCK + "stray line after the fence\n"
    with pytest.raises(AuthoringError, match="HUM-0003.*after the gold fence"):
        parse_authoring(junk)


needs_freeze = pytest.mark.skipif(
    not HUMAN_TEST.exists(), reason="human slice not yet frozen (step 1.8c authoring pending)"
)


@needs_freeze
def test_frozen_human_matches_manifest() -> None:
    manifest = json.loads(HUMAN_MANIFEST.read_text(encoding="utf-8"))
    frozen = HUMAN_TEST.read_text(encoding="utf-8")
    assert sha256_of(frozen) == manifest["sha256"]
    assert sha256_of(AUTHORING.read_text(encoding="utf-8")) == manifest["authoring_sha256"]
    assert 40 <= manifest["n"] <= 70


@needs_freeze
def test_frozen_human_equals_reparsed_authoring() -> None:
    records = parse_authoring(AUTHORING.read_text(encoding="utf-8"))
    assert to_jsonl(records) == HUMAN_TEST.read_text(encoding="utf-8")
