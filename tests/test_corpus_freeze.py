import json
from pathlib import Path

import pytest

from order_desk.corpus import ClassMix
from order_desk.materialize import (
    SPLIT_SIZES,
    allocate,
    build_all,
    sha256_of,
    to_jsonl,
)
from order_desk.schemas import EmailClass, ExtractedOrder

ROOT = Path(__file__).resolve().parent.parent
FROZEN = ROOT / "data" / "corpus" / "test.jsonl"
MANIFEST = ROOT / "data" / "corpus" / "MANIFEST.json"


@pytest.fixture(scope="module")
def built():
    return build_all()


def test_allocator_is_exact_and_deterministic() -> None:
    mix = ClassMix()
    for n in (1000, 500, 4500, 997):
        counts = allocate(n, mix)
        assert sum(counts.values()) == n
        assert counts == allocate(n, mix)
    assert allocate(1000, mix) == {
        EmailClass.NEW_ORDER: 700,
        EmailClass.AMENDMENT: 100,
        EmailClass.CANCELLATION: 50,
        EmailClass.INQUIRY: 100,
        EmailClass.OTHER: 50,
    }


def test_split_composition_matches_promise(built) -> None:
    splits, manifest = built
    assert {name: len(records) for name, records in splits.items()} == SPLIT_SIZES
    per = manifest["splits"]
    assert per["test"]["counts"] == {
        "new_order": 700,
        "amendment": 100,
        "cancellation": 50,
        "inquiry": 100,
        "other": 50,
    }
    assert per["val"]["counts"] == {
        "new_order": 350,
        "amendment": 50,
        "cancellation": 25,
        "inquiry": 50,
        "other": 25,
    }
    assert per["train"]["counts"] == {
        "new_order": 3150,
        "amendment": 450,
        "cancellation": 225,
        "inquiry": 450,
        "other": 225,
    }


def test_ids_are_namespaced_and_globally_unique(built) -> None:
    splits, _ = built
    all_ids = [record["id"] for records in splits.values() for record in records]
    assert len(set(all_ids)) == len(all_ids)
    prefix = {"train": "TRN-", "val": "VAL-", "test": "TST-"}
    for name, records in splits.items():
        assert all(record["id"].startswith(prefix[name]) for record in records)
        assert all(record["scenario"]["scenario_id"] == record["id"] for record in records)


def test_records_are_self_contained(built) -> None:
    splits, _ = built
    for records in splits.values():
        for record in records:
            cls = record["email_class"]
            if cls in ("new_order", "amendment"):
                assert record["gold_extraction"] is not None
                ExtractedOrder.model_validate(record["gold_extraction"])
            else:
                assert record["gold_extraction"] is None
            assert (record["oracle"] is not None) == (cls == "new_order")
            assert (record["render"] is not None) == (cls == "new_order")
            if cls == "other":
                misdirected = record["scenario"]["other_type"] == "misdirected"
                assert (record["customer_id"] is not None) == misdirected
            else:
                assert record["customer_id"] is not None


def test_frozen_bytes_and_manifest_match_regeneration(built) -> None:
    splits, manifest = built
    committed = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert committed == manifest, "MANIFEST.json is stale; rerun the materializer and commit"
    frozen = FROZEN.read_text(encoding="utf-8")
    assert sha256_of(frozen) == manifest["splits"]["test"]["sha256"]
    assert frozen == to_jsonl(splits["test"]), "frozen test drifted; see fixlog policy"


def test_duplicate_policy_tiers(built) -> None:
    _, manifest = built
    dup = manifest["duplicate_stats"]
    for cls in ("new_order", "amendment"):
        assert dup["test_in_train_or_val"][cls] == 0
        assert dup["val_in_train"][cls] == 0
