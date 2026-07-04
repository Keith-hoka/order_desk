import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from order_desk.harness import (
    Prediction,
    PredictionError,
    evaluate,
    load_frozen_human,
    load_predictions,
    load_source,
    reference_predictions,
)
from order_desk.materialize import to_jsonl

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def synthetic():
    return load_source("synthetic")


@pytest.fixture(scope="module")
def human():
    return load_source("human")


def _run(records, kind, sha, source, iterations=50, mutate=None):
    prediction_dicts = reference_predictions(records, kind)
    if mutate is not None:
        mutate(prediction_dicts)
    predictions = load_predictions(to_jsonl(prediction_dicts), [r["id"] for r in records])
    return evaluate(
        records,
        predictions,
        source=source,
        predictor=kind,
        dataset_sha=sha,
        iterations=iterations,
        seed=7,
    )


def test_prediction_contract_strictness() -> None:
    good = {
        "id": "X",
        "classification": "new_order",
        "extraction": {"raw": "{}", "parsed": None, "repair_used": False},
    }
    Prediction.model_validate(good)
    with pytest.raises(ValidationError):
        Prediction.model_validate({**good, "confidence": 0.9})
    strict = {
        "customer_po_text": None,
        "requested_date_text": None,
        "delivery_address_text": None,
        "buyer_name_text": None,
        "notes": None,
        "line_items": [
            {
                "product_text": "tape",
                "quantity": "6",
                "unit_text": None,
                "unit_price_text": None,
                "item_notes": None,
            }
        ],
    }
    with pytest.raises(ValidationError):
        Prediction.model_validate({**good, "extraction": {"raw": "", "parsed": strict}})


def test_load_predictions_completeness(synthetic) -> None:
    records, _sha = synthetic
    ids = [record["id"] for record in records]
    lines = to_jsonl(reference_predictions(records, "oracle")).splitlines()
    with pytest.raises(PredictionError, match="missing"):
        load_predictions("\n".join(lines[:-1]) + "\n", ids)
    with pytest.raises(PredictionError, match="duplicate"):
        load_predictions("\n".join([*lines, lines[0]]) + "\n", ids)
    tampered = json.loads(lines[0])
    tampered["id"] = "TST-GHOST-000000"
    with pytest.raises(PredictionError, match="unknown id"):
        load_predictions("\n".join([json.dumps(tampered), *lines[1:]]) + "\n", ids)


def test_oracle_synthetic_is_perfect(synthetic) -> None:
    records, sha = synthetic
    report = _run(records, "oracle", sha, "synthetic")
    assert report["dataset"]["n"] == 1000
    assert report["dataset"]["n_extraction"] == 800
    assert report["classification"]["accuracy"] == 1.0
    assert report["classification"]["order_missed"] == 0
    assert report["extraction"]["headline"]["f1"] == pytest.approx(1.0)
    assert report["extraction"]["headline"]["fp"] == 0
    assert report["extraction"]["headline"]["fn"] == 0
    assert report["ci"]["headline_f1"] == [1.0, 1.0]
    assert report["ci"]["accuracy"] == [1.0, 1.0]
    assert report["extraction"]["validity"]["attempted"] == 800
    assert len(report["slices"]) == 26
    assert all(row["n"] > 0 for row in report["slices"].values())
    trap = report["trap_items"]
    assert trap["items"] >= 50
    assert trap["match_rate"] == pytest.approx(1.0)
    assert all(value == pytest.approx(1.0) for value in trap["field_recall"].values())


def test_empty_synthetic_is_floor(synthetic) -> None:
    records, sha = synthetic
    report = _run(records, "empty", sha, "synthetic")
    assert report["classification"]["accuracy"] == 0.0
    assert report["classification"]["invalid_predictions"] == 1000
    assert report["classification"]["order_missed_rate"] == pytest.approx(1.0)
    assert report["extraction"]["headline"]["f1"] == 0.0
    assert report["extraction"]["headline"]["fn"] > 0
    assert report["extraction"]["headline"]["fp"] == 0
    assert report["ci"]["headline_f1"] == [0.0, 0.0]
    assert report["extraction"]["validity"]["parse_rate"] == 1.0
    assert report["trap_items"]["match_rate"] == 0.0


def test_oracle_human_is_perfect(human) -> None:
    records, sha = human
    report = _run(records, "oracle", sha, "human")
    assert report["dataset"]["n"] == 65
    assert report["dataset"]["n_extraction"] == 57
    assert report["classification"]["accuracy"] == 1.0
    assert report["extraction"]["headline"]["f1"] == pytest.approx(1.0)
    assert report["ci"]["accuracy"] == [1.0, 1.0]
    assert report["ci"]["macro_f1"] == [1.0, 1.0]
    assert report["trap_items"] is None
    assert len(report["slices"]) == 5


def test_human_pin_rejects_tamper(tmp_path) -> None:
    source_test = ROOT / "data" / "human" / "test_human.jsonl"
    source_manifest = ROOT / "data" / "human" / "MANIFEST.json"
    test_copy = tmp_path / "test_human.jsonl"
    manifest_copy = tmp_path / "MANIFEST.json"
    manifest_copy.write_text(source_manifest.read_text(encoding="utf-8"), encoding="utf-8")
    test_copy.write_text(source_test.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="sha256"):
        load_frozen_human(test_path=test_copy, manifest_path=manifest_copy)
    test_copy.write_text(source_test.read_text(encoding="utf-8"), encoding="utf-8")
    assert len(load_frozen_human(test_path=test_copy, manifest_path=manifest_copy)) == 65


def test_bootstrap_is_seeded_and_nondegenerate(human) -> None:
    records, sha = human

    def degrade(prediction_dicts):
        hit = 0
        for prediction in prediction_dicts:
            if prediction["extraction"] is None:
                continue
            hit += 1
            if hit % 3 == 0:
                prediction["classification"] = "inquiry"
                prediction["extraction"] = None

    first = _run(records, "oracle", sha, "human", iterations=200, mutate=degrade)
    second = _run(records, "oracle", sha, "human", iterations=200, mutate=degrade)
    assert first["ci"] == second["ci"]
    low, high = first["ci"]["accuracy"]
    assert low < high
    low_f1, high_f1 = first["ci"]["headline_f1"]
    assert low_f1 < high_f1
    low_m, high_m = first["ci"]["macro_f1"]
    assert low_m < high_m
    assert first["classification"]["order_missed"] > 0


def test_unattempted_extraction_scores_as_misses(human) -> None:
    records, _sha = human
    target = next(record for record in records if record["gold_extraction"] is not None)

    def drop(prediction_dicts):
        prediction_dicts[0]["extraction"] = None

    report = _run([target], "oracle", "x", "human", iterations=0, mutate=drop)
    assert report["extraction"]["validity"]["attempted"] == 0
    assert report["extraction"]["validity"]["parse_rate"] == 0.0
    assert report["extraction"]["headline"]["tp"] == 0
    assert report["extraction"]["headline"]["fn"] > 0
    assert report["ci"]["headline_f1"] is None
