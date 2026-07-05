"""Evaluation harness: loaders, prediction contract, slices, bootstrap (1.9b).

Semantics locked in step 1.9:

- Extraction is scored end-to-end over every gold-bearing record (new_order
  and amendment). A record whose prediction carries no extraction -- because
  classification routed it away or the predictor skipped it -- scores as the
  empty extraction; classification mistakes that lose an order therefore
  cost extraction recall too. attempted / parse_rate live in validity so the
  conditional story stays visible without becoming the headline.
- Prediction files are complete or rejected: unknown, duplicate, or missing
  ids are hard errors. A predictor cannot improve its numbers by omitting
  hard records.
- Reference predictors (oracle = gold echo, empty = all-null with a None
  classification) are written to disk and read back through the same loader
  as any future baseline, so the file contract is exercised end to end.
  empty's None classification scores as "invalid": order_missed_rate 1.0 by
  construction is the floor's definition.
- The trap-line slice is recall-oriented: pred-side hallucinations cannot be
  attributed to trap items, so it reports match rate and per-field recall
  only; unit_price_text is omitted because trap lines carry no price by
  construction. It reuses scoring's package-private _align_items.
- Bootstrap resamples records over compact per-record stats with a fixed
  seed; CIs cover the four top-level numbers only (headline F1, alignment
  F1, classification accuracy, macro-F1). Within a replicate, macro-F1
  averages over classes with gold support in that replicate: a class absent
  from a resample contributes no evidence, not a zero. This convention is
  EVAL_VERSION 2 -- under v1's impute-zero, a perfect predictor on the human
  slice drew a macro CI of [0.8, 1.0] purely because its support-2 class
  drops out of ~13% of replicates, violating the oracle known-answer
  invariant (reference predictors score perfectly, degenerate CIs
  included). Small-support fragility remains visible where it is real:
  accuracy is the classification headline on the human slice.
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from order_desk.audit import load_frozen_test
from order_desk.materialize import MANIFEST_PATH, sha256_of
from order_desk.scenarios import ScenarioFlags
from order_desk.schemas import EmailClass, ExtractedOrder
from order_desk.scoring import (
    EVAL_VERSION,
    HEADLINE_FIELDS,
    ClassificationTally,
    ExtractionTally,
    _align_items,
    _ratio,
    classification_metrics,
    empty_extraction,
    extraction_metrics,
    item_semantics,
    merge_tallies,
    norm_text,
    score_classification,
    score_extraction,
)

HUMAN_TEST = Path("data/human/test_human.jsonl")
HUMAN_MANIFEST = Path("data/human/MANIFEST.json")
BOOTSTRAP_SEED = 20260708
TRAP_FIELDS = ("product_text", "quantity", "unit_text")


class PredictionError(ValueError):
    """The prediction file is structurally invalid or incomplete."""


class PredictedExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str
    parsed: ExtractedOrder | None
    repair_used: bool = False


class Prediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    classification: str | None
    extraction: PredictedExtraction | None = None


def load_frozen_human(
    test_path: Path = HUMAN_TEST, manifest_path: Path = HUMAN_MANIFEST
) -> list[dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    text = test_path.read_text(encoding="utf-8")
    if sha256_of(text) != manifest["sha256"]:
        raise RuntimeError("data/human/test_human.jsonl does not match its MANIFEST sha256 pin")
    records = [json.loads(line) for line in text.splitlines()]
    if len(records) != manifest["n"]:
        raise RuntimeError("human slice record count does not match its manifest")
    return records


def load_source(source: str) -> tuple[list[dict[str, Any]], str]:
    if source == "synthetic":
        records = load_frozen_test()
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return records, manifest["splits"]["test"]["sha256"]
    if source == "human":
        records = load_frozen_human()
        manifest = json.loads(HUMAN_MANIFEST.read_text(encoding="utf-8"))
        return records, manifest["sha256"]
    raise ValueError(f"unknown source {source!r}")


def load_predictions(text: str, expected_ids: list[str]) -> dict[str, Prediction]:
    expected = set(expected_ids)
    out: dict[str, Prediction] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise PredictionError(f"line {lineno}: blank line")
        try:
            prediction = Prediction.model_validate_json(line)
        except ValidationError as exc:
            raise PredictionError(f"line {lineno}: {exc}") from exc
        if prediction.id not in expected:
            raise PredictionError(f"line {lineno}: unknown id {prediction.id!r}")
        if prediction.id in out:
            raise PredictionError(f"line {lineno}: duplicate id {prediction.id!r}")
        out[prediction.id] = prediction
    missing = [record_id for record_id in expected_ids if record_id not in out]
    if missing:
        head = ", ".join(missing[:5])
        raise PredictionError(f"{len(missing)} predictions missing (first: {head})")
    return out


def reference_predictions(records: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    if kind not in ("oracle", "empty"):
        raise ValueError(f"unknown reference predictor {kind!r}")
    predictions: list[dict[str, Any]] = []
    for record in records:
        extraction: dict[str, Any] | None = None
        if record["gold_extraction"] is not None:
            if kind == "oracle":
                extraction = {
                    "raw": json.dumps(record["gold_extraction"], sort_keys=True),
                    "parsed": record["gold_extraction"],
                    "repair_used": False,
                }
            else:
                extraction = {
                    "raw": "",
                    "parsed": empty_extraction().model_dump(),
                    "repair_used": False,
                }
        predictions.append(
            {
                "id": record["id"],
                "classification": record["email_class"] if kind == "oracle" else None,
                "extraction": extraction,
            }
        )
    return predictions


def _f1(tp: int, fp: int, fn: int) -> float:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * q
    lower = math.floor(k)
    upper = math.ceil(k)
    if lower == upper:
        return sorted_values[lower]
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (k - lower)


def _ci(values: list[float]) -> list[float] | None:
    if not values:
        return None
    ordered = sorted(values)
    return [_percentile(ordered, 0.025), _percentile(ordered, 0.975)]


def _bootstrap(
    ext_stats: list[tuple[int, int, int, int, int, int]],
    class_pairs: list[tuple[str, str]],
    iterations: int,
    seed: int,
) -> dict[str, list[float] | None]:
    rng = random.Random(seed)
    classes = [member.value for member in EmailClass]
    heads: list[float] = []
    aligns: list[float] = []
    accuracies: list[float] = []
    macros: list[float] = []
    n_ext, n_class = len(ext_stats), len(class_pairs)
    for _ in range(iterations):
        if n_ext:
            tp = fp = fn = align_tp = gold_items = pred_items = 0
            for _ in range(n_ext):
                stat = ext_stats[rng.randrange(n_ext)]
                tp += stat[0]
                fp += stat[1]
                fn += stat[2]
                align_tp += stat[3]
                gold_items += stat[4]
                pred_items += stat[5]
            heads.append(_f1(tp, fp, fn))
            aligns.append(_f1(align_tp, pred_items - align_tp, gold_items - align_tp))
        if n_class:
            confusion = Counter(class_pairs[rng.randrange(n_class)] for _ in range(n_class))
            accuracies.append(sum(confusion[(cls, cls)] for cls in classes) / n_class)
            f1_values = []
            for cls in classes:
                tp_c = confusion[(cls, cls)]
                fp_c = sum(v for (g, p), v in confusion.items() if p == cls and g != cls)
                fn_c = sum(v for (g, p), v in confusion.items() if g == cls and p != cls)
                if tp_c + fn_c == 0:
                    continue  # absent from this replicate's gold: no evidence, not zero
                f1_values.append(_f1(tp_c, fp_c, fn_c))
            macros.append(sum(f1_values) / len(f1_values) if f1_values else 0.0)
    return {
        "headline_f1": _ci(heads),
        "alignment_f1": _ci(aligns),
        "accuracy": _ci(accuracies),
        "macro_f1": _ci(macros),
    }


def _slice_specs(source: str) -> list[tuple[str, Callable[[dict[str, Any]], bool]]]:
    specs: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        (f"class:{member.value}", lambda r, v=member.value: r["email_class"] == v)
        for member in EmailClass
    ]
    if source != "synthetic":
        return specs
    for name in ScenarioFlags.model_fields:
        specs.append(
            (
                f"flag:{name}",
                lambda r, n=name: r["email_class"] == "new_order" and r["scenario"]["flags"][n],
            )
        )
    for route in ("touchless", "clarification", "exception"):
        specs.append(
            (
                f"route:{route}",
                lambda r, v=route: r["oracle"] is not None and r["oracle"]["route"] == v,
            )
        )
    for layout in ("dash_list", "x_list", "reverse_list", "prose"):
        specs.append(
            (
                f"layout:{layout}",
                lambda r, v=layout: r["render"] is not None and r["render"]["layout"] == v,
            )
        )
    for placement in ("subject_only", "body_only", "both"):
        specs.append(
            (
                f"po_placement:{placement}",
                lambda r, v=placement: r["render"] is not None and r["render"]["po_placement"] == v,
            )
        )
    return specs


def _slice_rows(
    records: list[dict[str, Any]],
    class_pairs: list[tuple[str, str]],
    ext_tallies: dict[str, ExtractionTally],
    source: str,
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for name, predicate in _slice_specs(source):
        members = [i for i, record in enumerate(records) if predicate(record)]
        correct = sum(1 for i in members if class_pairs[i][0] == class_pairs[i][1])
        gold_ids = [records[i]["id"] for i in members if records[i]["id"] in ext_tallies]
        row: dict[str, Any] = {
            "n": len(members),
            "accuracy": correct / len(members) if members else 0.0,
            "n_extraction": len(gold_ids),
        }
        if gold_ids:
            metrics = extraction_metrics(
                merge_tallies(ext_tallies[record_id] for record_id in gold_ids)
            )
            row["headline_f1"] = metrics["headline"]["f1"]
            row["alignment_f1"] = metrics["alignment"]["f1"]
        rows[name] = row
    return rows


def _trap_report(
    records: list[dict[str, Any]], predictions: dict[str, Prediction]
) -> dict[str, Any]:
    correct = dict.fromkeys(TRAP_FIELDS, 0)
    slots = dict.fromkeys(TRAP_FIELDS, 0)
    total_items = matched_items = trap_records = 0
    for record in records:
        if record["email_class"] != "new_order":
            continue
        scenario = record["scenario"]
        trap_indices = [
            i for i, item in enumerate(scenario["items"]) if item["intended_packs"] is not None
        ]
        if not trap_indices:
            continue
        trap_records += 1
        gold = ExtractedOrder.model_validate(record["gold_extraction"])
        prediction = predictions[record["id"]]
        parsed = prediction.extraction.parsed if prediction.extraction is not None else None
        pred_items = parsed.line_items if parsed is not None else []
        pairs, _greedy = _align_items(gold.line_items, pred_items)
        matched = dict(pairs)
        for i in trap_indices:
            total_items += 1
            gold_item = gold.line_items[i]
            j = matched.get(i)
            if j is not None:
                matched_items += 1
            for field_name in TRAP_FIELDS:
                gold_value = getattr(gold_item, field_name)
                if gold_value is None:
                    continue
                slots[field_name] += 1
                if j is None:
                    continue
                pred_value = getattr(pred_items[j], field_name)
                if pred_value is None:
                    continue
                if field_name == "quantity":
                    hit = gold_value == pred_value
                else:
                    hit = norm_text(gold_value) == norm_text(pred_value)
                correct[field_name] += 1 if hit else 0
    return {
        "records": trap_records,
        "items": total_items,
        "match_rate": matched_items / total_items if total_items else 0.0,
        "field_recall": {
            name: correct[name] / slots[name] if slots[name] else 0.0 for name in TRAP_FIELDS
        },
        "note": "unit_price_text omitted: trap lines carry no price by construction",
    }


def _item_semantics_report(
    records: list[dict[str, Any]], predictions: dict[str, Prediction]
) -> dict[str, Any]:
    """Aggregate the segmentation-independent diagnostic over gold-bearing records."""
    totals = {
        "anchorable_gold": 0,
        "anchorable_pred": 0,
        "matched": 0,
        "product_exact": 0,
        "product_contains": 0,
        "quantity_hit": 0,
        "unit_hit": 0,
    }
    for record in records:
        if record["gold_extraction"] is None:
            continue
        gold = ExtractedOrder.model_validate(record["gold_extraction"])
        prediction = predictions[record["id"]]
        parsed = prediction.extraction.parsed if prediction.extraction is not None else None
        pred = ExtractedOrder.model_validate(parsed) if parsed is not None else None
        for key, value in item_semantics(gold, pred).items():
            totals[key] += value
    matched = totals["matched"]
    return {
        **totals,
        "match_rate": _ratio(matched, totals["anchorable_gold"]),
        "product_exact_rate": _ratio(totals["product_exact"], matched),
        "product_contains_rate": _ratio(totals["product_contains"], matched),
        "span_gap": _ratio(totals["product_contains"] - totals["product_exact"], matched),
        "unit_hit_rate": _ratio(totals["unit_hit"], matched),
    }


def evaluate(
    records: list[dict[str, Any]],
    predictions: dict[str, Prediction],
    *,
    source: str,
    predictor: str,
    dataset_sha: str,
    iterations: int = 1000,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    valid_classes = {member.value for member in EmailClass}
    class_tally = ClassificationTally()
    class_pairs: list[tuple[str, str]] = []
    ext_tallies: dict[str, ExtractionTally] = {}
    ext_stats: list[tuple[int, int, int, int, int, int]] = []
    attempted = 0
    extraction_on_non_gold = 0

    for record in records:
        prediction = predictions[record["id"]]
        gold_class = record["email_class"]
        pred_class = (
            prediction.classification if prediction.classification in valid_classes else "invalid"
        )
        class_tally.absorb(score_classification(gold_class, prediction.classification))
        class_pairs.append((gold_class, pred_class))
        if record["gold_extraction"] is None:
            if prediction.extraction is not None:
                extraction_on_non_gold += 1
            continue
        gold = ExtractedOrder.model_validate(record["gold_extraction"])
        if prediction.extraction is None:
            tally = score_extraction(gold, None)
        else:
            attempted += 1
            tally = score_extraction(
                gold,
                prediction.extraction.parsed,
                repair_used=prediction.extraction.repair_used,
            )
        ext_tallies[record["id"]] = tally
        tp = sum(tally.fields[name].tp for name in HEADLINE_FIELDS)
        fp = sum(tally.fields[name].fp for name in HEADLINE_FIELDS)
        fn = sum(tally.fields[name].fn for name in HEADLINE_FIELDS)
        align = tally.alignment
        ext_stats.append((tp, fp, fn, align.product_correct, align.gold_items, align.pred_items))

    ext_metrics = extraction_metrics(merge_tallies(ext_tallies.values()))
    ext_metrics["validity"]["attempted"] = attempted
    ext_metrics["validity"]["attempted_rate"] = attempted / len(ext_tallies) if ext_tallies else 0.0
    ext_metrics["validity"]["extraction_on_non_gold"] = extraction_on_non_gold

    report: dict[str, Any] = {
        "eval_version": EVAL_VERSION,
        "predictor": predictor,
        "source": source,
        "dataset": {
            "n": len(records),
            "n_extraction": len(ext_tallies),
            "sha256": dataset_sha,
        },
        "bootstrap": {"iterations": iterations, "seed": seed},
        "classification": classification_metrics(class_tally),
        "extraction": ext_metrics,
        "ci": _bootstrap(ext_stats, class_pairs, iterations, seed)
        if iterations > 0
        else {"headline_f1": None, "alignment_f1": None, "accuracy": None, "macro_f1": None},
        "slices": _slice_rows(records, class_pairs, ext_tallies, source),
        "trap_items": _trap_report(records, predictions) if source == "synthetic" else None,
        "item_semantics": _item_semantics_report(records, predictions)
        if source == "synthetic"
        else None,
    }
    return report


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def _fmt_ci(ci: list[float] | None) -> str:
    if ci is None:
        return "[--, --]"
    return f"[{ci[0]:.4f}, {ci[1]:.4f}]"


def report_markdown(report: dict[str, Any]) -> str:
    classification = report["classification"]
    extraction = report["extraction"]
    ci = report["ci"]
    dataset = report["dataset"]
    lines = [
        f"# Eval report — {report['predictor']} on {report['source']}",
        "",
        f"- eval_version: {report['eval_version']}",
        f"- dataset: n={dataset['n']} (extraction {dataset['n_extraction']}), "
        f"sha256 {dataset['sha256'][:16]}",
        f"- bootstrap: {report['bootstrap']['iterations']} iterations, "
        f"seed {report['bootstrap']['seed']}",
        "",
        "## Classification",
        "",
        f"- accuracy: {_fmt(classification['accuracy'])} {_fmt_ci(ci['accuracy'])}",
        f"- macro_f1: {_fmt(classification['macro_f1'])} {_fmt_ci(ci['macro_f1'])}",
        f"- order_missed_rate: {_fmt(classification['order_missed_rate'])} "
        f"({classification['order_missed']} missed)",
        f"- invalid_predictions: {classification['invalid_predictions']}",
        "",
        "| class | precision | recall | f1 | support |",
        "|---|---|---|---|---|",
    ]
    for cls, row in classification["per_class"].items():
        lines.append(
            f"| {cls} | {_fmt(row['precision'])} | {_fmt(row['recall'])} "
            f"| {_fmt(row['f1'])} | {row['support']} |"
        )
    headline = extraction["headline"]
    validity = extraction["validity"]
    alignment = extraction["alignment"]
    lines += [
        "",
        "## Extraction",
        "",
        f"- headline: P {_fmt(headline['precision'])} / R {_fmt(headline['recall'])} / "
        f"F1 {_fmt(headline['f1'])} {_fmt_ci(ci['headline_f1'])}",
        f"- strict_rate: {_fmt(headline['strict_rate'])}   "
        f"hallucination_rate: {_fmt(headline['hallucination_rate'])}",
        f"- alignment_f1: {_fmt(alignment['f1'])} {_fmt_ci(ci['alignment_f1'])} "
        f"(matched {alignment['matched']}/{alignment['gold_items']} gold, "
        f"{alignment['pred_items']} pred, greedy_runs {alignment['greedy_runs']})",
        f"- validity: attempted {validity['attempted']}/{extraction['records']}, "
        f"parse_rate {_fmt(validity['parse_rate'])}, repair_rate {_fmt(validity['repair_rate'])}, "
        f"extraction_on_non_gold {validity['extraction_on_non_gold']}",
        "",
        "| field | precision | recall | f1 | halluc_rate | accuracy | strict |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, row in extraction["fields"].items():
        lines.append(
            f"| {name} | {_fmt(row['precision'])} | {_fmt(row['recall'])} | {_fmt(row['f1'])} "
            f"| {_fmt(row['hallucination_rate'])} | {_fmt(row['accuracy'])} "
            f"| {_fmt(row['strict_rate'])} |"
        )
    lines += ["", "| notes field | token_p | token_r | token_f1 |", "|---|---|---|---|"]
    for name, row in extraction["notes"].items():
        lines.append(
            f"| {name} | {_fmt(row['token_precision'])} | {_fmt(row['token_recall'])} "
            f"| {_fmt(row['token_f1'])} |"
        )
    lines += [
        "",
        "## Slices",
        "",
        "| slice | n | accuracy | n_ext | headline_f1 | alignment_f1 |",
        "|---|---|---|---|---|---|",
    ]
    for name, row in report["slices"].items():
        headline_cell = _fmt(row["headline_f1"]) if "headline_f1" in row else "--"
        align_cell = _fmt(row["alignment_f1"]) if "alignment_f1" in row else "--"
        lines.append(
            f"| {name} | {row['n']} | {_fmt(row['accuracy'])} | {row['n_extraction']} "
            f"| {headline_cell} | {align_cell} |"
        )
    trap = report["trap_items"]
    if trap is not None:
        lines += [
            "",
            "## Trap-line items (recall-oriented)",
            "",
            f"- records: {trap['records']}, items: {trap['items']}, "
            f"match_rate: {_fmt(trap['match_rate'])}",
            f"- note: {trap['note']}",
            "",
            "| field | recall |",
            "|---|---|",
        ]
        for name, value in trap["field_recall"].items():
            lines.append(f"| {name} | {_fmt(value)} |")
    lines.append("")
    return "\n".join(lines)
