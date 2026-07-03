"""Run the eval harness: reference predictors or an external prediction file."""

import argparse
import json
import sys
from pathlib import Path

from order_desk.harness import (
    BOOTSTRAP_SEED,
    PredictionError,
    evaluate,
    load_predictions,
    load_source,
    reference_predictions,
    report_markdown,
)
from order_desk.materialize import to_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("synthetic", "human"), required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--predictor", choices=("oracle", "empty"))
    group.add_argument("--predictions", type=Path)
    parser.add_argument("--name", default=None, help="report name for --predictions mode")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()

    records, sha = load_source(args.source)
    ids = [record["id"] for record in records]

    if args.predictor:
        name = args.predictor
        prediction_dicts = reference_predictions(records, args.predictor)
        pred_dir = args.out / "predictions"
        pred_dir.mkdir(parents=True, exist_ok=True)
        pred_path = pred_dir / f"{name}_{args.source}.jsonl"
        pred_path.write_text(to_jsonl(prediction_dicts), encoding="utf-8")
        print(f"wrote {pred_path}")
        text = pred_path.read_text(encoding="utf-8")
    else:
        name = args.name or args.predictions.stem
        text = args.predictions.read_text(encoding="utf-8")

    try:
        predictions = load_predictions(text, ids)
    except PredictionError as exc:
        sys.exit(f"INVALID: {exc}")

    report = evaluate(
        records,
        predictions,
        source=args.source,
        predictor=name,
        dataset_sha=sha,
        iterations=args.iterations,
        seed=args.seed,
    )

    report_dir = args.out / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"{name}_{args.source}.json"
    md_path = report_dir / f"{name}_{args.source}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(report_markdown(report), encoding="utf-8")

    classification = report["classification"]
    extraction = report["extraction"]
    ci = report["ci"]
    dataset = report["dataset"]

    def fmt_ci(values):
        return f"[{values[0]:.4f}, {values[1]:.4f}]" if values else "[--, --]"

    print(
        f"eval_version={report['eval_version']} source={args.source} predictor={name} "
        f"n={dataset['n']} extraction={dataset['n_extraction']} sha={dataset['sha256'][:16]}"
    )
    print(
        f"classification: accuracy={classification['accuracy']:.4f} {fmt_ci(ci['accuracy'])} "
        f"macro_f1={classification['macro_f1']:.4f} {fmt_ci(ci['macro_f1'])} "
        f"order_missed_rate={classification['order_missed_rate']:.4f} "
        f"invalid={classification['invalid_predictions']}"
    )
    headline = extraction["headline"]
    print(
        f"extraction: headline_f1={headline['f1']:.4f} {fmt_ci(ci['headline_f1'])} "
        f"alignment_f1={extraction['alignment']['f1']:.4f} {fmt_ci(ci['alignment_f1'])} "
        f"strict_rate={headline['strict_rate']:.4f} "
        f"hallucination_rate={headline['hallucination_rate']:.4f}"
    )
    validity = extraction["validity"]
    print(
        f"validity: attempted={validity['attempted']}/{extraction['records']} "
        f"parse_rate={validity['parse_rate']:.4f} repair_rate={validity['repair_rate']:.4f} "
        f"extraction_on_non_gold={validity['extraction_on_non_gold']}"
    )
    trap = report["trap_items"]
    trap_note = (
        f" trap: records={trap['records']} items={trap['items']} "
        f"match_rate={trap['match_rate']:.4f}"
        if trap is not None
        else ""
    )
    print(f"slices={len(report['slices'])}{trap_note}")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
