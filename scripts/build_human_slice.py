"""Validate the human authoring file; freeze data/human/test_human.jsonl."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from order_desk.catalog import load_catalog
from order_desk.customers import load_customers
from order_desk.human import AuthoringError, parse_authoring
from order_desk.materialize import build_all, sha256_of, to_jsonl

AUTHORING = Path("data/human/authoring.md")
HUMAN_TEST = Path("data/human/test_human.jsonl")
HUMAN_MANIFEST = Path("data/human/MANIFEST.json")
HARD_TOTAL = (40, 70)
HARD_NEW_ORDER_MIN = 30


def coverage_rows(records):
    catalog, book = load_catalog(), load_customers()
    tone_by = {c.customer_id: c.style.tone for c in book.customers}
    multi = {c.customer_id for c in book.customers if len(c.delivery_addresses) > 1}
    orders = [r for r in records if r["email_class"] == "new_order"]

    def items(record):
        return record["gold_extraction"]["line_items"]

    def count(predicate):
        return sum(1 for record in orders if predicate(record))

    return [
        ("new_order: no PO", 8, count(lambda r: r["gold_extraction"]["customer_po_text"] is None)),
        (
            "new_order: stated prices",
            6,
            count(lambda r: any(i["unit_price_text"] for i in items(r))),
        ),
        (
            "new_order: missing quantity",
            6,
            count(lambda r: any(i["quantity"] is None for i in items(r))),
        ),
        (
            "new_order: multi-site, no address",
            5,
            count(
                lambda r: (
                    r["customer_id"] in multi
                    and r["gold_extraction"]["delivery_address_text"] is None
                )
            ),
        ),
        (
            "new_order: unresolvable product",
            5,
            count(lambda r: any(catalog.resolve_sku(i["product_text"]) is None for i in items(r))),
        ),
        (
            "new_order: unresolvable unit",
            4,
            count(
                lambda r: any(
                    i["unit_text"] and catalog.resolve_unit(i["unit_text"]) is None
                    for i in items(r)
                )
            ),
        ),
        ("distinct customers", 6, len({r["customer_id"] for r in records if r["customer_id"]})),
        (
            "tones covered",
            3,
            len({tone_by[r["customer_id"]] for r in records if r["customer_id"]}),
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="validate and report; write nothing")
    parser.add_argument("--refreeze", action="store_true", help="overwrite the frozen human slice")
    parser.add_argument("--entry", default=None, help="fixlog entry text authorizing --refreeze")
    args = parser.parse_args()

    if not AUTHORING.exists():
        sys.exit(f"AUTHORING MISSING: {AUTHORING} not found -- see docs/human_slice_guide.md")
    authoring_text = AUTHORING.read_text(encoding="utf-8")
    try:
        records = parse_authoring(authoring_text)
    except AuthoringError as exc:
        sys.exit(f"INVALID: {exc}")

    splits, _ = build_all()
    synthetic_keys = {r["subject"] + "\x1f" + r["body"] for split in splits.values() for r in split}
    collisions = [r["id"] for r in records if (r["subject"] + "\x1f" + r["body"]) in synthetic_keys]
    if collisions:
        sys.exit(f"FATAL: exact collision with synthetic corpus: {', '.join(collisions)}")

    counts = Counter(record["email_class"] for record in records)
    print(f"records: {len(records)}")
    for cls, count in sorted(counts.items()):
        print(f"  {cls:<14} {count}")
    print("\nsoft coverage (target -> got):")
    for name, target, got in coverage_rows(records):
        mark = "" if got >= target else "   <- below target"
        print(f"  {name:<36} {target:>3} -> {got:>3}{mark}")

    if args.preview:
        print("\npreview only -- nothing written")
        return

    total = len(records)
    if not (HARD_TOTAL[0] <= total <= HARD_TOTAL[1]) or counts["new_order"] < HARD_NEW_ORDER_MIN:
        sys.exit(
            f"REFUSED: freeze requires {HARD_TOTAL[0]}..{HARD_TOTAL[1]} records with "
            f">= {HARD_NEW_ORDER_MIN} new_order (got {total} / {counts['new_order']})"
        )

    jsonl_text = to_jsonl(records)
    if HUMAN_TEST.exists() and HUMAN_TEST.read_text(encoding="utf-8") != jsonl_text:
        if not args.refreeze:
            sys.exit(
                "REFUSED: regenerated human slice differs from frozen "
                "data/human/test_human.jsonl. If intentional, rerun with "
                "--refreeze --entry (entry-before-refreeze; see the fixlog ritual)."
            )
        fixlog = Path("docs/frozen_test_fixlog.md").read_text(encoding="utf-8")
        if not args.entry or args.entry not in fixlog:
            sys.exit(
                "REFUSED: --refreeze requires --entry TEXT already present in\n"
                "docs/frozen_test_fixlog.md (entry-before-refreeze; see the ritual)."
            )
        HUMAN_TEST.write_text(jsonl_text, encoding="utf-8")
        print(f"\nREFROZE {HUMAN_TEST} ({total} records)")
    elif HUMAN_TEST.exists():
        print(f"\nhuman freeze intact: {HUMAN_TEST} matches the authoring file")
    else:
        HUMAN_TEST.parent.mkdir(parents=True, exist_ok=True)
        HUMAN_TEST.write_text(jsonl_text, encoding="utf-8")
        print(f"\nfroze {HUMAN_TEST} ({total} records)")

    manifest = {
        "version": 1,
        "n": total,
        "counts": dict(sorted(counts.items())),
        "sha256": sha256_of(jsonl_text),
        "authoring_sha256": sha256_of(authoring_text),
        "frozen_files": ["data/human/test_human.jsonl"],
    }
    HUMAN_MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {HUMAN_MANIFEST}")
    print(f"  sha256={manifest['sha256']}")


if __name__ == "__main__":
    main()
