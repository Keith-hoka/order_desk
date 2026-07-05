import json
from pathlib import Path

import pytest

from order_desk.prompts import extraction_system_prompt, prompt_bundle_hash
from order_desk.schemas import ExtractedOrder
from order_desk.sft import (
    build_example,
    build_manifest,
    build_sft_pool,
    build_val_gold,
    canonical_assistant,
    curve_subsets,
)

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "sft" / "MANIFEST.json"


@pytest.fixture(scope="module")
def pool():
    return build_sft_pool()


@pytest.fixture(scope="module")
def subsets(pool):
    return curve_subsets(pool)


def test_canonical_assistant_validates_and_is_idempotent() -> None:
    gold = {
        "customer_po_text": "PO-1",
        "requested_date_text": None,
        "delivery_address_text": "Botany",
        "buyer_name_text": "Dana",
        "notes": None,
        "line_items": [
            {
                "product_text": "clear tape",
                "quantity": 6,
                "unit_text": "rolls",
                "unit_price_text": None,
                "item_notes": None,
            }
        ],
    }
    text = canonical_assistant(gold)
    assert ExtractedOrder.model_validate_json(text)
    assert canonical_assistant(json.loads(text)) == text


def test_examples_use_pinned_contract_and_valid_targets(pool) -> None:
    assert len(pool) > 3000
    system = extraction_system_prompt()
    for example in pool[:200]:
        system_msg, user_msg, assistant_msg = example["messages"]
        assert system_msg == {"role": "system", "content": system}
        assert user_msg["role"] == "user" and user_msg["content"].startswith("Subject: ")
        assert assistant_msg["role"] == "assistant"
        ExtractedOrder.model_validate_json(assistant_msg["content"])


def test_pool_is_train_only_and_gold_bearing(pool) -> None:
    assert all(example["id"].startswith("TRN-") for example in pool)
    ids = [example["id"] for example in pool]
    assert len(set(ids)) == len(ids)


def test_curve_subsets_are_nested_prefixes(pool, subsets) -> None:
    assert set(subsets) == {"500", "1000", "2000", "full"}
    assert [e["id"] for e in subsets["500"]] == [e["id"] for e in pool[:500]]
    assert [e["id"] for e in subsets["1000"]][:500] == [e["id"] for e in subsets["500"]]
    assert [e["id"] for e in subsets["2000"]][:1000] == [e["id"] for e in subsets["1000"]]
    assert subsets["full"] == pool


def test_build_example_rejects_non_gold() -> None:
    with pytest.raises(RuntimeError, match="non-gold"):
        build_example({"id": "TRN-X", "gold_extraction": None})


def test_manifest_matches_committed(pool, subsets) -> None:
    live = build_manifest(pool, subsets)
    committed = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert committed == live, "SFT manifest is stale; rerun scripts/build_sft.py and commit"
    assert live["prompt_bundle_hash"] == prompt_bundle_hash()
    assert live["pool_size"] == len(pool)


def test_manifest_asserts_eval_purity(pool, subsets) -> None:
    manifest = build_manifest(pool, subsets)
    assert manifest["subsets"]["full"]["composition"]["n"] == len(pool)
    assert manifest["subsets"]["full"]["composition"]["amendment"] > 0
    assert manifest["subsets"]["full"]["composition"]["new_order"] > 0


def test_val_gold_is_val_namespace_and_gold_bearing() -> None:
    val = build_val_gold()
    assert len(val) > 0
    assert all(example["id"].startswith("VAL-") for example in val)
    system = extraction_system_prompt()
    for example in val[:50]:
        assert example["messages"][0] == {"role": "system", "content": system}
        ExtractedOrder.model_validate_json(example["messages"][2]["content"])
