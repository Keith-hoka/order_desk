"""Audit-pack sampler over the frozen test split (step 1.8a).

Coverage-first sampling: per-class budgets are soft targets, coverage minima
are hard. Every stratum is guaranteed its minimum via a greedy pass (rarest
stratum first, picks credited to every stratum they belong to), then each
class is filled to its target with a uniform draw. Sampling is deterministic
(AUDIT_SEED) and pinned to the frozen bytes: the sampler refuses to run if
data/corpus/test.jsonl no longer matches the sha256 in MANIFEST.json.

The verdict file will carry hours of human labor, so it gets freeze-like
protection: build_audit_pack never overwrites a verdicts.jsonl whose ids
differ from the computed sample, and leaves a consistent one untouched.
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

from order_desk.customers import CustomerBook, load_customers
from order_desk.materialize import FROZEN_TEST, MANIFEST_PATH, sha256_of

AUDIT_SEED = 20260706
AUDIT_DIR = Path("data/audit")
SAMPLE_IDS_PATH = AUDIT_DIR / "sample_ids.json"
SHEET_PATH = AUDIT_DIR / "audit_sheet.md"
VERDICTS_PATH = AUDIT_DIR / "verdicts.jsonl"

NEW_ORDER_TARGET = 72
CLASS_TARGETS: dict[str, int] = {
    "amendment": 18,
    "cancellation": 10,
    "inquiry": 12,
    "other": 8,
}
FLAG_MIN = 6

Predicate = Callable[[dict[str, Any]], bool]

PROTOCOL = """# Audit sheet — frozen test subsample (step 1.8)

Fill data/audit/verdicts.jsonl in place: one JSON line per record, same
order as this sheet. Set the two booleans, add notes where useful. Do not
reorder or delete lines; multiple sittings are fine.

- **realistic** — read as an ops person at a packaging supplier: could this
  email land in your inbox without feeling machine-written? Judge the quirk
  ledger from docs/corpus_notes.md here and tag notes accordingly
  (`quirk:a jarring`, `quirk:b fine`). Ledger shorthand: (a) singular
  canonical units ("20 roll of"); (b) item notes mismatched to the product;
  (c) unsigned personal-mailbox emails ending at a bare sign-off; (d) the
  (a) family inside amendment glue.
- **labels_correct** — is everything we claim true? Class label; every
  gold_extraction field verbatim-correct including nulls (null means the
  email does not state it — an empty string or paraphrase is a fail); for
  new_order, the oracle line (route / asks / violations) per SPEC §1. For
  cancellation / inquiry / other there is no gold: judge the class label
  and, for cancellation, the referenced PO or temporal phrase.
- **Audit, do not fix.** Defects are findings recorded in verdicts; fixes go
  through the fixlog/refreeze ritual in step 1.8b, never by editing frozen
  files.

The `focus:` line under a record names the strata it was sampled to cover —
check those aspects with extra care, then judge the record as a whole.

---
"""


def load_frozen_test(
    test_path: Path = FROZEN_TEST, manifest_path: Path = MANIFEST_PATH
) -> list[dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    text = test_path.read_text(encoding="utf-8")
    pinned = manifest["splits"]["test"]["sha256"]
    if sha256_of(text) != pinned:
        raise RuntimeError("data/corpus/test.jsonl does not match the MANIFEST sha256 pin")
    return [json.loads(line) for line in text.splitlines()]


def _sender_role(record: dict[str, Any], book: CustomerBook) -> str | None:
    customer = book.resolve_customer(record["sender_email"])
    if customer is None:
        return None
    for contact in customer.contacts:
        if contact.email == record["sender_email"]:
            return contact.role
    return None


def _new_order_strata(book: CustomerBook) -> list[tuple[str, int, Predicate]]:
    strata: list[tuple[str, int, Predicate]] = []
    flag_names = (
        "missing_po",
        "missing_quantity",
        "ambiguous_site",
        "discontinued_item",
        "qty_below_moq",
        "qty_above_max",
        "pack_size_trap",
        "mention_typo",
        "unsigned",
        "prices_stated",
        "price_mismatch",
    )
    for name in flag_names:
        strata.append((f"flag:{name}", FLAG_MIN, lambda r, n=name: r["scenario"]["flags"][n]))
    for route in ("touchless", "clarification", "exception"):
        strata.append((f"route:{route}", 10, lambda r, v=route: r["oracle"]["route"] == v))
    for layout in ("dash_list", "x_list", "reverse_list", "prose"):
        strata.append((f"layout:{layout}", 8, lambda r, v=layout: r["render"]["layout"] == v))
    for placement in ("subject_only", "body_only", "both"):
        strata.append(
            (
                f"po_placement:{placement}",
                5,
                lambda r, v=placement: r["render"]["po_placement"] == v,
            )
        )
    strata.append(
        (
            "quirk_a:canonical_unit",
            8,
            lambda r: any(i["unit_style"] == "canonical" for i in r["scenario"]["items"]),
        )
    )
    strata.append(
        (
            "quirk_b:item_note",
            8,
            lambda r: any(i["item_note"] for i in r["scenario"]["items"]),
        )
    )
    strata.append(
        (
            "quirk_c:unsigned_personal",
            6,
            lambda r: (
                r["scenario"]["flags"]["unsigned"]
                and _sender_role(r, book) not in (None, "shared mailbox")
            ),
        )
    )
    return strata


def _class_strata(cls: str) -> list[tuple[str, int, Predicate]]:
    if cls == "amendment":
        strata: list[tuple[str, int, Predicate]] = [
            (f"change:{v}", 4, lambda r, v=v: r["scenario"]["change_type"] == v)
            for v in ("qty_change", "add_item", "remove_item", "date_change")
        ]
        strata.append(("ref:po", 6, lambda r: r["scenario"]["referenced_po"] is not None))
        strata.append(("ref:temporal", 6, lambda r: r["scenario"]["temporal_ref"] is not None))
        return strata
    if cls == "cancellation":
        return [
            ("ref:po", 4, lambda r: r["scenario"]["referenced_po"] is not None),
            ("ref:temporal", 4, lambda r: r["scenario"]["temporal_ref"] is not None),
        ]
    if cls == "inquiry":
        return [
            (f"type:{v}", 4, lambda r, v=v: r["scenario"]["inquiry_type"] == v)
            for v in ("quote_request", "stock_check", "general")
        ]
    return [
        (f"type:{v}", 2, lambda r, v=v: r["scenario"]["other_type"] == v)
        for v in ("vendor_marketing", "misdirected", "courier_notice")
    ]


def _greedy(
    pool: list[dict[str, Any]],
    strata: list[tuple[str, int, Predicate]],
    target: int,
    rng: random.Random,
    label: str,
) -> list[str]:
    members: dict[str, list[str]] = {}
    for name, minimum, predicate in strata:
        ids = [record["id"] for record in pool if predicate(record)]
        if len(ids) < minimum:
            raise RuntimeError(f"{label}/{name}: only {len(ids)} candidates for minimum {minimum}")
        members[name] = ids
    selected: list[str] = []
    chosen: set[str] = set()
    for name, minimum, _ in sorted(strata, key=lambda s: len(members[s[0]])):
        have = sum(1 for i in members[name] if i in chosen)
        need = minimum - have
        if need > 0:
            candidates = [i for i in members[name] if i not in chosen]
            for pick in rng.sample(candidates, need):
                selected.append(pick)
                chosen.add(pick)
    remaining = [record["id"] for record in pool if record["id"] not in chosen]
    fill = target - len(selected)
    if fill > 0:
        for pick in rng.sample(remaining, min(fill, len(remaining))):
            selected.append(pick)
            chosen.add(pick)
    return sorted(selected)


def _subtype(record: dict[str, Any]) -> str:
    scenario = record["scenario"]
    for key in ("change_type", "inquiry_type", "other_type"):
        if key in scenario:
            return scenario[key]
    return ""


def _block(seq: int, record: dict[str, Any], focus: list[str]) -> str:
    head = f"### {seq:03d} · {record['id']} · {record['email_class']}"
    subtype = _subtype(record)
    if subtype:
        head += f" / {subtype}"
    lines = [
        head,
        "",
        f"From: {record['sender_email']}    Sent: {record['sent_at']}",
        f"Subject: {record['subject']}",
        "",
        "```text",
        record["body"].rstrip("\n"),
        "```",
        "",
    ]
    if record["gold_extraction"] is not None:
        gold = json.dumps(record["gold_extraction"], indent=2, ensure_ascii=False, sort_keys=True)
        lines += ["gold_extraction:", "```json", gold, "```", ""]
    if record["oracle"] is not None:
        oracle = record["oracle"]
        lines.append(
            f"oracle: route={oracle['route']}  asks={oracle['asks']}  "
            f"violations={oracle['violations']}"
        )
    if focus:
        lines.append("focus: " + ", ".join(focus))
    lines.append("")
    return "\n".join(lines)


def build_pack(records: list[dict[str, Any]]) -> dict[str, Any]:
    book = load_customers()
    rng = random.Random(AUDIT_SEED)
    by_class: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_class.setdefault(record["email_class"], []).append(record)

    order_strata = _new_order_strata(book)
    ids = _greedy(by_class["new_order"], order_strata, NEW_ORDER_TARGET, rng, "new_order")
    for cls, target in CLASS_TARGETS.items():
        ids += _greedy(by_class[cls], _class_strata(cls), target, rng, cls)

    index = {record["id"]: record for record in records}
    picked = [index[i] for i in ids]

    coverage_rows: list[tuple[str, int, int]] = []
    for name, minimum, predicate in order_strata:
        got = sum(1 for r in picked if r["email_class"] == "new_order" and predicate(r))
        coverage_rows.append((f"new_order/{name}", minimum, got))
    for cls in CLASS_TARGETS:
        for name, minimum, predicate in _class_strata(cls):
            got = sum(1 for r in picked if r["email_class"] == cls and predicate(r))
            coverage_rows.append((f"{cls}/{name}", minimum, got))

    blocks = []
    for seq, record in enumerate(picked, start=1):
        focus = (
            [name for name, _, predicate in order_strata if predicate(record)]
            if record["email_class"] == "new_order"
            else []
        )
        blocks.append(_block(seq, record, focus))
    sheet = PROTOCOL + "\n".join(blocks)

    verdicts = "".join(
        json.dumps(
            {"id": i, "realistic": None, "labels_correct": None, "notes": ""}, sort_keys=True
        )
        + "\n"
        for i in ids
    )
    return {"ids": ids, "sheet": sheet, "verdicts": verdicts, "coverage_rows": coverage_rows}
