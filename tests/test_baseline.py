import json
from pathlib import Path

import pytest

from order_desk.baseline import (
    ResponseCache,
    StageResult,
    normalize_label,
    parse_extraction,
    repair_json_text,
    run_baseline,
    summarize_sidecar,
    write_run,
)
from order_desk.harness import evaluate, load_predictions, load_source
from order_desk.prompts import prompt_bundle_hash

EMPTY_JSON = json.dumps(
    {
        "customer_po_text": None,
        "requested_date_text": None,
        "delivery_address_text": None,
        "buyer_name_text": None,
        "notes": None,
        "line_items": [],
    }
)


class FakeClient:
    def __init__(self, script: dict[tuple[str, str], str]) -> None:
        self.script = script
        self.calls: list[tuple[str, str]] = []

    def run_stage(self, stage, system, user, record_id) -> StageResult:
        assert system and user.startswith("Subject: ")
        self.calls.append((record_id, stage))
        n = len(self.calls)
        return StageResult(
            raw=self.script[(record_id, stage)],
            input_tokens=100 + n,
            output_tokens=10 + n,
            latency_s=0.01 * n,
        )


@pytest.fixture(scope="module")
def human():
    return load_source("human")


def test_parse_and_repair_variants() -> None:
    direct, used = parse_extraction(EMPTY_JSON)
    assert direct is not None and used is False
    fenced, used = parse_extraction(f"```json\n{EMPTY_JSON}\n```")
    assert fenced is not None and used is True
    wrapped, used = parse_extraction(f"Here you go:\n{EMPTY_JSON}\nHope that helps!")
    assert wrapped is not None and used is True
    nothing, used = parse_extraction("no json here at all")
    assert nothing is None and used is False
    assert repair_json_text("no braces anywhere") is None
    bad_schema = EMPTY_JSON.replace(
        '"line_items": []',
        '"line_items": [{"product_text": "tape", "quantity": "6", "unit_text": null,'
        ' "unit_price_text": null, "item_notes": null}]',
    )
    parsed, used = parse_extraction(bad_schema)
    assert parsed is None and used is False


def test_label_normalization() -> None:
    assert normalize_label(" New_Order.\n") == "new_order"
    assert normalize_label('"inquiry"') == "inquiry"
    assert normalize_label("`cancellation`") == "cancellation"
    assert normalize_label("Amendment") == "amendment"
    assert normalize_label("banana!") == "banana!"
    assert normalize_label("   ") is None


def test_cache_roundtrip_and_stale_entries(tmp_path: Path) -> None:
    cache = ResponseCache(tmp_path, "model-x", "default", prompt_bundle_hash())
    assert cache.get("R1", "classify") is None
    result = StageResult(raw="new_order", input_tokens=5, output_tokens=1, latency_s=0.2)
    cache.put("R1", "classify", result)
    assert cache.get("R1", "classify") == result
    path = cache.dir / "R1.classify.json"
    entry = json.loads(path.read_text(encoding="utf-8"))
    entry["prompt_hash"] = "0" * 64
    path.write_text(json.dumps(entry), encoding="utf-8")
    assert cache.get("R1", "classify") is None


def test_pipeline_end_to_end_through_harness(human, tmp_path_factory) -> None:
    records_all, sha = human
    orders = [r for r in records_all if r["email_class"] == "new_order"][:4]
    inquiries = [r for r in records_all if r["email_class"] == "inquiry"][:2]
    records = orders + inquiries
    gold_json = [json.dumps(r["gold_extraction"], sort_keys=True) for r in orders]
    script = {
        (orders[0]["id"], "classify"): "new_order",
        (orders[0]["id"], "extract"): gold_json[0],
        (orders[1]["id"], "classify"): "New_Order",
        (orders[1]["id"], "extract"): f"```json\n{gold_json[1]}\n```",
        (orders[2]["id"], "classify"): "new_order",
        (orders[2]["id"], "extract"): "sorry, cannot help with that",
        (orders[3]["id"], "classify"): "inquiry",
        (inquiries[0]["id"], "classify"): "inquiry",
        (inquiries[1]["id"], "classify"): "new_order",
        (inquiries[1]["id"], "extract"): EMPTY_JSON,
    }
    client = FakeClient(script)
    cache_root = tmp_path_factory.mktemp("cache")
    predictions, sidecar = run_baseline(
        records, client, model="fake/model-1", cache_root=cache_root
    )
    assert (orders[3]["id"], "extract") not in client.calls
    extract_calls = sorted(rid for rid, stage in client.calls if stage == "extract")
    assert extract_calls == sorted(
        [orders[0]["id"], orders[1]["id"], orders[2]["id"], inquiries[1]["id"]]
    )
    assert len(client.calls) == 6 + 4  # spend follows the predicted class: false positives pay too

    pred_path, side_path = write_run(
        "fake", "human", predictions, sidecar, out_dir=tmp_path_factory.mktemp("out")
    )
    loaded = load_predictions(pred_path.read_text(encoding="utf-8"), [r["id"] for r in records])
    report = evaluate(
        records, loaded, source="human", predictor="fake", dataset_sha=sha, iterations=0
    )

    validity = report["extraction"]["validity"]
    assert report["extraction"]["records"] == 4
    assert validity["attempted"] == 3
    assert validity["parse_rate"] == pytest.approx(0.5)
    assert validity["repair_rate"] == pytest.approx(0.25)
    assert validity["extraction_on_non_gold"] == 1
    assert report["classification"]["order_missed"] == 1
    assert report["classification"]["accuracy"] == pytest.approx(4 / 6)
    assert report["extraction"]["headline"]["fp"] == 0
    assert report["extraction"]["headline"]["fn"] > 0
    assert side_path.read_text(encoding="utf-8").count("\n") == len(sidecar)

    silent = FakeClient({})
    predictions_again, sidecar_again = run_baseline(
        records, silent, model="fake/model-1", cache_root=cache_root
    )
    assert silent.calls == []
    assert predictions_again == predictions
    assert all(row["cached"] for row in sidecar_again)


def test_sidecar_summary_counts_fresh_only() -> None:
    rows = [
        {
            "id": "a",
            "stage": "classify",
            "cached": False,
            "latency_s": 0.2,
            "input_tokens": 100,
            "output_tokens": 5,
        },
        {
            "id": "a",
            "stage": "extract",
            "cached": False,
            "latency_s": 0.4,
            "input_tokens": 200,
            "output_tokens": 50,
        },
        {
            "id": "b",
            "stage": "classify",
            "cached": True,
            "latency_s": 0.0,
            "input_tokens": 100,
            "output_tokens": 5,
        },
    ]
    summary = summarize_sidecar(rows)
    assert (summary["calls"], summary["cached"], summary["fresh"]) == (3, 1, 2)
    assert summary["input_tokens"] == 300
    assert summary["output_tokens"] == 55
    assert summary["latency_p50"] == pytest.approx(0.3)
    assert summary["latency_p95"] == pytest.approx(0.39)
