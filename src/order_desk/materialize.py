"""Corpus materialization and the one-time test freeze (step 1.7).

Split design: every split draws from its own derived generator streams, so
train can grow later without perturbing a byte of the frozen test split. IDs
are namespaced per split (TRN-/VAL-/TST-) for global uniqueness and so each
split's render stream is keyed independently.

Freeze semantics: data/corpus/test.jsonl is the frozen object. A default run
refuses to change it -- it regenerates everything in memory, byte-compares
the test split, and only rewrites the regenerable train/val files. Changing
frozen bytes requires --refreeze plus an entry in docs/frozen_test_fixlog.md.
tests/test_corpus_freeze.py enforces the same property in CI.

Record schema (one JSON object per line, sorted keys, UTF-8): id,
email_class, subject, body, sender_email, sent_at, customer_id,
gold_extraction (new_order and amendment; null otherwise), oracle
{route, asks, violations} (new_order only; pins oracle drift), render
{layout, po_placement} (new_order only; render-time choices are not part of
scenario provenance but are needed for per-slice error analysis), scenario
(full provenance dump).
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from order_desk.catalog import Catalog, load_catalog
from order_desk.corpus import ClassMix, MixedItem, derive_seed, render_item, verify_item
from order_desk.customers import CustomerBook, load_customers
from order_desk.nonorder import (
    AmendmentScenario,
    RenderedMessage,
    generate_amendments,
    generate_cancellations,
    generate_inquiries,
    generate_others,
)
from order_desk.renderer import RenderedEmail
from order_desk.scenarios import OrderScenario, generate_scenarios
from order_desk.schemas import EmailClass

CORPUS_SEED = 20260705
SPLIT_SIZES: dict[str, int] = {"train": 4500, "val": 500, "test": 1000}
SPLIT_PREFIX: dict[str, str] = {"train": "TRN", "val": "VAL", "test": "TST"}
CORPUS_DIR = Path("data/corpus")
FROZEN_TEST = CORPUS_DIR / "test.jsonl"
MANIFEST_PATH = CORPUS_DIR / "MANIFEST.json"

GENERATORS = {
    EmailClass.NEW_ORDER: generate_scenarios,
    EmailClass.AMENDMENT: generate_amendments,
    EmailClass.CANCELLATION: generate_cancellations,
    EmailClass.INQUIRY: generate_inquiries,
    EmailClass.OTHER: generate_others,
}


def allocate(n: int, mix: ClassMix) -> dict[EmailClass, int]:
    """Largest-remainder apportionment; deterministic tie-break by enum order."""
    exact = {cls: n * weight for cls, weight in mix.weights.items()}
    counts = {cls: int(exact[cls]) for cls in mix.weights}
    remainder = n - sum(counts.values())
    order = sorted(
        mix.weights,
        key=lambda cls: (-(exact[cls] - counts[cls]), list(EmailClass).index(cls)),
    )
    for cls in order[:remainder]:
        counts[cls] += 1
    return counts


def _record(
    item: MixedItem,
    rendered: RenderedEmail | RenderedMessage,
    catalog: Catalog,
    book: CustomerBook,
) -> dict[str, Any]:
    gold: dict[str, Any] | None = None
    oracle: dict[str, Any] | None = None
    render_meta: dict[str, Any] | None = None
    if isinstance(item, OrderScenario):
        gold = item.gold_extraction().model_dump()
        oracle = {
            "route": item.expected_route(catalog, book).value,
            "asks": [a.value for a in item.expected_asks(book)],
            "violations": [v.value for v in item.expected_violations(catalog)],
        }
        assert isinstance(rendered, RenderedEmail)
        render_meta = {
            "layout": rendered.layout.value,
            "po_placement": rendered.po_placement.value if rendered.po_placement else None,
        }
    elif isinstance(item, AmendmentScenario):
        gold = item.gold_extraction().model_dump()
    return {
        "id": item.scenario_id,
        "email_class": item.email_class.value,
        "subject": rendered.subject,
        "body": rendered.body,
        "sender_email": item.sender_email,
        "sent_at": item.sent_at.isoformat(),
        "customer_id": item.customer_id,
        "gold_extraction": gold,
        "oracle": oracle,
        "render": render_meta,
        "scenario": item.model_dump(mode="json"),
    }


def build_split(split: str, n: int, seed: int, mix: ClassMix | None = None) -> list[dict[str, Any]]:
    """Generate, render, contract-verify, and record one split."""
    mix = mix or ClassMix()
    catalog, book = load_catalog(), load_customers()
    prefix = SPLIT_PREFIX[split]
    scenarios: list[MixedItem] = []
    for cls, count in allocate(n, mix).items():
        if not count:
            continue
        for item in GENERATORS[cls](count, derive_seed(seed, f"{split}|{cls.value}")):
            scenarios.append(
                item.model_copy(update={"scenario_id": f"{prefix}-{item.scenario_id}"})
            )
    random.Random(f"{seed}|{split}|shuffle").shuffle(scenarios)
    render_seed = derive_seed(seed, f"{split}|render")
    records: list[dict[str, Any]] = []
    for item in scenarios:
        rendered = render_item(item, render_seed)
        verify_item(item, rendered)
        records.append(_record(item, rendered, catalog, book))
    return records


def to_jsonl(records: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n" for record in records
    )


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def duplicate_stats(splits: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, int]]:
    """Exact subject+body collisions across splits, per class (measured, tiered)."""

    def key(record: dict[str, Any]) -> str:
        return record["subject"] + "\x1f" + record["body"]

    def key_sets(name: str) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {cls.value: set() for cls in EmailClass}
        for record in splits[name]:
            out[record["email_class"]].add(key(record))
        return out

    train, val = key_sets("train"), key_sets("val")

    def overlap(records: list[dict[str, Any]], *pools: dict[str, set[str]]) -> dict[str, int]:
        counts = {cls.value: 0 for cls in EmailClass}
        for record in records:
            if any(key(record) in pool[record["email_class"]] for pool in pools):
                counts[record["email_class"]] += 1
        return counts

    return {
        "test_in_train_or_val": overlap(splits["test"], train, val),
        "val_in_train": overlap(splits["val"], train),
    }


def build_all(
    seed: int = CORPUS_SEED,
    sizes: dict[str, int] | None = None,
    mix: ClassMix | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    sizes = sizes or SPLIT_SIZES
    mix = mix or ClassMix()
    splits = {name: build_split(name, n, seed, mix) for name, n in sizes.items()}
    dup = duplicate_stats(splits)
    for cls in (EmailClass.NEW_ORDER, EmailClass.AMENDMENT):
        for label, per_class in dup.items():
            if per_class[cls.value]:
                raise RuntimeError(f"cross-split duplicate for {cls.value} in {label}: {per_class}")
    manifest = {
        "version": 1,
        "corpus_seed": seed,
        "splits": {
            name: {
                "n": len(records),
                "counts": {cls.value: c for cls, c in allocate(sizes[name], mix).items()},
                "sha256": sha256_of(to_jsonl(records)),
            }
            for name, records in splits.items()
        },
        "duplicate_stats": dup,
        "frozen_files": ["data/corpus/test.jsonl"],
    }
    return splits, manifest


def manifest_to_text(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"
