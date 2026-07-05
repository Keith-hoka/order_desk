"""SFT dataset construction from the frozen train split (step 3.1).

The training file is a pure function of the train split and the pinned
prompt contract -- fully regenerable, so it is hash-pinned rather than
ritually frozen: data/sft/MANIFEST.json records the train-split sha, the
prompt-bundle hash, and each curve subset's sha, and CI regenerates and
compares. Change the train split or the prompt contract and the hashes move.

Locked decisions:
- Each example is {"messages": [system, user, assistant]} in message form
  (not a chat-template-applied string): applying the Qwen3 template is the
  trainer's job (step 3.2), so the data stays model-agnostic.
- system/user come from the pinned prompt contract (extraction_system_prompt
  + format_email); assistant is the gold_extraction as canonical JSON
  (sort_keys, ensure_ascii=False), matching the harness wire format.
- Every assistant string must validate against ExtractedOrder AND re-dump to
  itself byte-for-byte (idempotent canonical form) -- the training target is
  in-contract and canonical, enforced at build time.
- Curve subsets are nested prefixes (one seeded shuffle, then the first
  500/1000/2000/full) so the data-scaling curve's points are comparable.
- Every SFT id carries the TRN- prefix; the build asserts zero overlap with
  val/test namespaces, making "never trained on the frozen eval" a
  build-time invariant, not a promise.
"""

from __future__ import annotations

import json
import random
from typing import Any

from order_desk.materialize import build_all, sha256_of, to_jsonl
from order_desk.prompts import extraction_system_prompt, format_email, prompt_bundle_hash
from order_desk.schemas import ExtractedOrder

SFT_SHUFFLE_SEED = 20260710
CURVE_SIZES = (500, 1000, 2000)  # full is appended at build time
GOLD_CLASSES = frozenset({"new_order", "amendment"})


def canonical_assistant(gold: dict[str, Any]) -> str:
    """Canonical JSON target; validated and idempotent by construction."""
    order = ExtractedOrder.model_validate(gold)
    text = json.dumps(order.model_dump(), sort_keys=True, ensure_ascii=False)
    reparsed = ExtractedOrder.model_validate_json(text)
    redumped = json.dumps(reparsed.model_dump(), sort_keys=True, ensure_ascii=False)
    if text != redumped:
        raise RuntimeError("assistant JSON is not idempotent under canonical dump")
    return text


def build_example(record: dict[str, Any]) -> dict[str, Any]:
    if record["gold_extraction"] is None:
        raise RuntimeError(f"{record['id']}: non-gold record cannot be an SFT example")
    return {
        "id": record["id"],
        "messages": [
            {"role": "system", "content": extraction_system_prompt()},
            {"role": "user", "content": format_email(record["subject"], record["body"])},
            {"role": "assistant", "content": canonical_assistant(record["gold_extraction"])},
        ],
    }


def build_sft_pool(seed: int = SFT_SHUFFLE_SEED) -> list[dict[str, Any]]:
    """Every gold-bearing train record as a shuffled SFT example list."""
    splits, _ = build_all()
    train = splits["train"]
    for record in train:
        if not record["id"].startswith("TRN-"):
            raise RuntimeError(f"train split leaked a non-TRN id: {record['id']}")
    gold_records = [r for r in train if r["email_class"] in GOLD_CLASSES]
    examples = [build_example(record) for record in gold_records]
    random.Random(f"{seed}|sft-shuffle").shuffle(examples)
    return examples


def curve_subsets(pool: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Nested prefixes: 500, 1000, 2000, full (full = len(pool))."""
    sizes = [n for n in CURVE_SIZES if n < len(pool)] + [len(pool)]
    subsets: dict[str, list[dict[str, Any]]] = {}
    for n in sizes:
        label = "full" if n == len(pool) else str(n)
        subsets[label] = pool[:n]
    return subsets


def _composition(examples: list[dict[str, Any]], ids_to_class: dict[str, str]) -> dict[str, Any]:
    classes = [ids_to_class[e["id"]] for e in examples]
    line_counts = [len(json.loads(e["messages"][2]["content"])["line_items"]) for e in examples]
    return {
        "n": len(examples),
        "new_order": classes.count("new_order"),
        "amendment": classes.count("amendment"),
        "avg_line_items": round(sum(line_counts) / len(line_counts), 3) if line_counts else 0.0,
    }


def build_manifest(
    pool: list[dict[str, Any]], subsets: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    splits, _ = build_all()
    train_sha = sha256_of(to_jsonl(splits["train"]))
    ids_to_class = {r["id"]: r["email_class"] for r in splits["train"]}
    val_test_ids = {r["id"] for name in ("val", "test") for r in splits[name]}
    overlap = {e["id"] for e in pool} & val_test_ids
    if overlap:
        raise RuntimeError(f"SFT pool overlaps frozen eval ids: {sorted(overlap)[:5]}")
    return {
        "version": 1,
        "shuffle_seed": SFT_SHUFFLE_SEED,
        "train_split_sha256": train_sha,
        "prompt_bundle_hash": prompt_bundle_hash(),
        "pool_size": len(pool),
        "subsets": {
            label: {
                "sha256": sha256_of(to_jsonl(examples)),
                "composition": _composition(examples, ids_to_class),
            }
            for label, examples in subsets.items()
        },
    }
