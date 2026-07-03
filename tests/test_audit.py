import json
from collections import Counter
from pathlib import Path

import pytest

from order_desk.audit import build_pack, load_frozen_test

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def records():
    return load_frozen_test()


@pytest.fixture(scope="module")
def pack(records):
    return build_pack(records)


def test_sampler_is_deterministic(records, pack) -> None:
    assert build_pack(records)["ids"] == pack["ids"]


def test_sample_ids_are_unique_and_from_frozen_test(records, pack) -> None:
    ids = pack["ids"]
    assert len(set(ids)) == len(ids)
    assert set(ids) <= {record["id"] for record in records}


def test_composition_bands(records, pack) -> None:
    index = {record["id"]: record["email_class"] for record in records}
    counts = Counter(index[i] for i in pack["ids"])
    assert 72 <= counts["new_order"] <= 90
    assert 18 <= counts["amendment"] <= 22
    assert counts["cancellation"] == 10
    assert counts["inquiry"] == 12
    assert counts["other"] == 8
    assert 120 <= len(pack["ids"]) <= 142


def test_coverage_minima_hold(pack) -> None:
    for name, minimum, got in pack["coverage_rows"]:
        assert got >= minimum, (name, minimum, got)


def test_verdict_template_matches_ids(pack) -> None:
    lines = pack["verdicts"].splitlines()
    assert [json.loads(line)["id"] for line in lines] == pack["ids"]
    for line in lines:
        verdict = json.loads(line)
        assert set(verdict) == {"id", "realistic", "labels_correct", "notes"}
        assert verdict["realistic"] is None
        assert verdict["labels_correct"] is None
        assert verdict["notes"] == ""


def test_sheet_lists_every_sampled_record_once(pack) -> None:
    for record_id in pack["ids"]:
        assert pack["sheet"].count(f"· {record_id} ·") == 1


def test_hash_pin_rejects_tampered_frozen_file(tmp_path) -> None:
    source_test = ROOT / "data" / "corpus" / "test.jsonl"
    source_manifest = ROOT / "data" / "corpus" / "MANIFEST.json"
    test_copy = tmp_path / "test.jsonl"
    manifest_copy = tmp_path / "MANIFEST.json"
    text = source_test.read_text(encoding="utf-8")
    manifest_copy.write_text(source_manifest.read_text(encoding="utf-8"), encoding="utf-8")

    test_copy.write_text(text + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="sha256"):
        load_frozen_test(test_path=test_copy, manifest_path=manifest_copy)

    test_copy.write_text(text, encoding="utf-8")
    assert len(load_frozen_test(test_path=test_copy, manifest_path=manifest_copy)) == 1000
